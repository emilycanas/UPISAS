from EventManager.Models.RunnerEvents import RunnerEvents
from EventManager.EventSubscriptionController import EventSubscriptionController
from ConfigValidator.Config.Models.RunTableModel import RunTableModel
from ConfigValidator.Config.Models.FactorModel import FactorModel
from ConfigValidator.Config.Models.RunnerContext import RunnerContext
from ConfigValidator.Config.Models.OperationType import OperationType
from ExtendedTyping.Typing import SupportsStr
from ProgressManager.Output.OutputProcedure import OutputProcedure as output

from typing import Dict, Optional
from pathlib import Path
from os.path import dirname, realpath
import subprocess
import time

from UPISAS.exemplars.ramses import RAMSES
from UPISAS.strategies.empty_strategy import EmptyStrategy
from UPISAS.strategies.naive_strategy import NaiveStrategy
from UPISAS.run_recorder import RunRecorder

# This file is in <course folder>/UPISAS/UPISAS/experiment_runner_configs/,
# so the course folder (with the RAMSES package and the challenge helpers) is 3 levels up
CONFIG_DIR = Path(dirname(realpath(__file__)))
COURSE_DIR = CONFIG_DIR.parents[2]
RESET_SCRIPT = COURSE_DIR / "ramses-challenge-1" / "helpers" / "reset_ramses.sh"
RUN_ALL = COURSE_DIR / "SEAMS24_artifact_package" / "bash_scripts" / "execute" / "RUN_ALL.sh"

ROUND_SECONDS = 5           # one monitor round every 5 s, like run_experiment.py
SETTLE_SECONDS = 30         # extra wait after a reset, so all services are registered

# Strategy name (as in the run table) -> strategy class
STRATEGIES = {
    "empty": EmptyStrategy,
    "naive": NaiveStrategy,
}


class RunnerConfig:
    ROOT_DIR = CONFIG_DIR

    # ================================ USER SPECIFIC CONFIG ================================
    """The name of the experiment."""
    name:                       str             = "ramses_baseline"

    """Results go to experiment_runner_configs/experiments/<name> (ignored by git)."""
    results_output_path:        Path            = ROOT_DIR / 'experiments'

    """Run everything automatically, one run after the other."""
    operation_type:             OperationType   = OperationType.AUTO

    """Wait after each run. The reset in before_run already takes a few minutes."""
    time_between_runs_in_ms:    int             = 1000

    def __init__(self):
        """Executes immediately after program start, on config load"""

        EventSubscriptionController.subscribe_to_multiple_events([
            (RunnerEvents.BEFORE_EXPERIMENT, self.before_experiment),
            (RunnerEvents.BEFORE_RUN       , self.before_run       ),
            (RunnerEvents.START_RUN        , self.start_run        ),
            (RunnerEvents.START_MEASUREMENT, self.start_measurement),
            (RunnerEvents.INTERACT         , self.interact         ),
            (RunnerEvents.STOP_MEASUREMENT , self.stop_measurement ),
            (RunnerEvents.STOP_RUN         , self.stop_run         ),
            (RunnerEvents.POPULATE_RUN_DATA, self.populate_run_data),
            (RunnerEvents.AFTER_EXPERIMENT , self.after_experiment )
        ])
        self.run_table_model = None  # Initialized later

        # Set per run in start_run()
        self.exemplar = None
        self.strategy = None
        self.strategy_name = None
        self.recorder = None
        self.summary = None

        output.console_log("RAMSES config loaded")

    def create_run_table_model(self) -> RunTableModel:
        """Every combination of strategy and scenario, 3 times each (18 runs).
        Shuffled, so a slow period of the laptop doesn't hit only one strategy."""
        strategy_factor = FactorModel("strategy", ["empty", "naive"])
        scenario_factor = FactorModel("scenario", ["default", "custom1", "custom2"])
        self.run_table_model = RunTableModel(
            factors=[strategy_factor, scenario_factor],
            repetitions=3,
            shuffle=True,
            data_columns=["availability", "time_within_800ms", "average_instances", "utility"]
        )
        return self.run_table_model

    def before_experiment(self) -> None:
        """Check once that the reset script and RUN_ALL.sh are where we expect them."""
        if not RESET_SCRIPT.exists():
            raise FileNotFoundError(f"reset script not found: {RESET_SCRIPT}")
        if not RUN_ALL.exists():
            raise FileNotFoundError(f"RUN_ALL.sh not found: {RUN_ALL}")
        output.console_log("Remember: socat and the interface must be running in their own terminals.")

    def before_run(self) -> None:
        """Every run starts on a fresh RAMSES, so instances or LB weights left
        over from the previous run cannot affect the next one."""
        output.console_log("Resetting RAMSES (takes a few minutes)...")
        subprocess.run(["bash", str(RESET_SCRIPT), str(RUN_ALL)], check=True)
        time.sleep(SETTLE_SECONDS)

    def start_run(self, context: RunnerContext) -> None:
        """Create the scenario, the strategy and the recorder for this run."""
        self.strategy_name = context.run_variation["strategy"]
        scenario_name = context.run_variation["scenario"]

        self.exemplar = RAMSES(scenario_name)
        strategy_class = STRATEGIES[self.strategy_name]
        self.strategy = strategy_class(self.exemplar)

        self.exemplar.start_run()
        # The recorder writes into this run's own folder
        self.recorder = RunRecorder(self.strategy_name, scenario_name, folder=str(context.run_dir))
        output.console_log(f"Run started: {self.strategy_name} on {scenario_name}")

    def start_measurement(self, context: RunnerContext) -> None:
        pass   # the recorder measures inside interact()

    def interact(self, context: RunnerContext) -> None:
        """The same loop as run_experiment.py, for as long as the scenario lasts."""
        start = time.monotonic()
        while time.monotonic() - start < self.exemplar.run_seconds:
            try:
                self.strategy.monitor(with_validation=False)
                self.recorder.record(self.strategy.knowledge.monitored_data)

                # No adaptation: only monitor and record (EmptyStrategy's analyze()
                # and plan() return True, so it would send empty actions otherwise)
                if self.strategy_name != "empty":
                    if self.strategy.analyze() and self.strategy.plan():
                        self.strategy.execute(self.strategy.knowledge.plan_data, with_validation=False)
                        print(self.strategy.knowledge.analysis_data)
            except Exception as e:
                print(e)
            time.sleep(ROUND_SECONDS - (time.monotonic() - start) % ROUND_SECONDS)

    def stop_measurement(self, context: RunnerContext) -> None:
        self.summary = self.recorder.summary()

    def stop_run(self, context: RunnerContext) -> None:
        # The next reset removes the container anyway; this just stops the scenario now
        try:
            self.exemplar.stop_container()
        except Exception as e:
            print(f"Could not stop the scenario container: {e}")

    def populate_run_data(self, context: RunnerContext) -> Optional[Dict[str, SupportsStr]]:
        """One row per run in run_table.csv."""
        return {
            "availability": round(self.summary["availability"], 4),
            "time_within_800ms": round(self.summary["time_within_800ms"], 4),
            "average_instances": round(self.summary["average_instances"], 3),
            "utility": round(self.summary["utility"], 4),
        }

    def after_experiment(self) -> None:
        output.console_log("Experiment finished. Results: run_table.csv in the experiment folder.")

    # ================================ DO NOT ALTER BELOW THIS LINE ================================
    experiment_path:            Path             = None
