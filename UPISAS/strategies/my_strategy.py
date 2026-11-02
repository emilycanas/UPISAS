from UPISAS.strategy import Strategy

# UPISAS/strategies/my_strategy.py 
# In analyze(), use the monitored data to detect that RESTAURANT-SERVICE has lost its instance. 
# In plan(), decide what to do in the given scenario to beat the baseline strategy's availability.

class MyStrategy(Strategy):

    def analyze(self):
        data = self.knowledge.monitored_data
        print(data)
        mean_f = sum(data["f"])/len(data["f"])
        print("[Analysis]\tmean_f: " + str(mean_f))
        if mean_f > 0:
            self.knowledge.analysis_data["mean_f"] = mean_f
            return True
        return False

    def plan(self):
        data = self.knowledge.analysis_data["mean_f"]
        if data > 0:
            self.knowledge.plan_data = {"x": 2, "y": 5}
            return True
        return False
