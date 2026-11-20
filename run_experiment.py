import time

from UPISAS.exemplars.ramses import RAMSES
from UPISAS.strategies.naive_strategy import NaiveStrategy 

exemplar = RAMSES()
strategy = NaiveStrategy(exemplar)
exemplar.start_run()

start = time.monotonic()
while time.monotonic() - start < 300:
    try:
        strategy.monitor(with_validation=False)
        if strategy.analyze() and strategy.plan():
            strategy.execute(strategy.knowledge.plan_data, with_validation=False)
            print(strategy.knowledge.analysis_data)
    except Exception as e:
        print(e)
    time.sleep(5 - (time.monotonic() - start) % 5)

exemplar.stop_container()
