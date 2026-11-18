import time

from UPISAS.exemplars.ramses import RAMSES
from UPISAS.strategies.mpc_strategy import MPCStrategy

exemplar = RAMSES()
strategy = MPCStrategy(exemplar)
exemplar.start_run()

start = time.monotonic()
while time.monotonic() - start < 240:
    try:
        strategy.monitor(with_validation=False)
        if strategy.analyze() and strategy.plan():
            strategy.execute(strategy.knowledge.plan_data, with_validation=False)
    except Exception as e:
        print(e)
    time.sleep(5 - (time.monotonic() - start) % 5)

exemplar.stop_container()
