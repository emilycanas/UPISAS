import time

from UPISAS.exemplars.ramses import RAMSES
from UPISAS.strategies.naive_strategy import NaiveStrategy 
from UPISAS.run_recorder import RunRecorder

exemplar = RAMSES()
strategy = NaiveStrategy(exemplar)
exemplar.start_run()
recorder = RunRecorder("naive", "default")

start = time.monotonic()
while time.monotonic() - start < 300:
    try:
        strategy.monitor(with_validation=False)
        recorder.record(strategy.knowledge.monitored_data)
        if strategy.analyze() and strategy.plan():
            strategy.execute(strategy.knowledge.plan_data, with_validation=False)
            print(strategy.knowledge.analysis_data)
    except Exception as e:
        print(e)
    time.sleep(5 - (time.monotonic() - start) % 5)

recorder.summary()
exemplar.stop_container()
