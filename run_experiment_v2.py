import logging
import time
import traceback

from UPISAS.exemplars.ramses import RAMSES
from UPISAS.strategies.mpc_strategy_v2 import MPCStrategy

RUN_SECONDS = 240     # the challenge scenario: 4 minutes, failure at 120 s
ROUND_SECONDS = 5     # one MAPE-K round every 5 s

logging.getLogger().setLevel(logging.WARNING) 

exemplar = RAMSES()
strategy = MPCStrategy(exemplar)
exemplar.start_run()

try:
    start = time.monotonic()
    while time.monotonic() - start < RUN_SECONDS:
        try:
            strategy.monitor(with_validation=False)
            if strategy.analyze() and strategy.plan():
                strategy.execute(strategy.knowledge.plan_data, with_validation=False)
        except Exception:
            traceback.print_exc()
        time.sleep(ROUND_SECONDS - (time.monotonic() - start) % ROUND_SECONDS)
finally:
    strategy.log.summary()
    try:
        exemplar.stop_container()
    except Exception:
        traceback.print_exc()
        print("Could not stop the container (Docker did not answer). "
              "Reset RAMSES before the next run, see the notes.")