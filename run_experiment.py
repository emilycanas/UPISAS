import time

from UPISAS.exemplars.ramses import RAMSES
from UPISAS.strategies.empty_strategy import EmptyStrategy
from UPISAS.strategies.naive_strategy import NaiveStrategy
from UPISAS.run_recorder import RunRecorder

# ---------- Settings: change these for each run ----------
STRATEGY = "naive"       # "empty" (no adaptation) or "naive" (baseline); later "mpc"
SCENARIO = "default"     # name for the result files only, it does not change the scenario
RUN_SECONDS = 300        # 5 minutes, like the Challenge 2 scenarios
ROUND_SECONDS = 5        # one monitor round every 5 s

exemplar = RAMSES()

# Pick the strategy. "empty" still needs a Strategy object, because monitor()
# lives in Strategy, but it never adapts (see the loop below).
if STRATEGY == "empty":
    strategy = EmptyStrategy(exemplar)
elif STRATEGY == "naive":
    strategy = NaiveStrategy(exemplar)
else:
    raise ValueError(f"unknown strategy: {STRATEGY}")

exemplar.start_run()
recorder = RunRecorder(STRATEGY, SCENARIO)

start = time.monotonic()
while time.monotonic() - start < RUN_SECONDS:
    try:
        strategy.monitor(with_validation=False)
        recorder.record(strategy.knowledge.monitored_data)

        # No adaptation: only monitor and record. EmptyStrategy's analyze() and
        # plan() return True, so without this check it would send an empty
        # action to RAMSES every round.
        if STRATEGY != "empty":
            if strategy.analyze() and strategy.plan():
                strategy.execute(strategy.knowledge.plan_data, with_validation=False)
                print(strategy.knowledge.analysis_data)
    except Exception as e:
        print(e)
    time.sleep(ROUND_SECONDS - (time.monotonic() - start) % ROUND_SECONDS)

recorder.summary()
exemplar.stop_container()
