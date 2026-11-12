from UPISAS.strategy import Strategy

# UPISAS/strategies/my_strategy.py 
# In analyze(), use the monitored data to detect that RESTAURANT-SERVICE has lost its instance. 
# In plan(), decide what to do in the given scenario to beat the baseline strategy's availability.

class MyStrategy(Strategy):
    def __init__(self, exemplar):
        super().__init__(exemplar)
        self.last_add = None

    def analyze(self): # pyright: ignore[reportIncompatibleMethodOverride]
        data = self.knowledge.monitored_data
        latest = data["services"][-1]

        # Case 1: the restaurant service has disappeard from the data
        if "RESTAURANT-SERVICE" not in latest:
            print("[Analyze]: restaurant service is gone")
            return True
        
        restaurant = latest["RESTAURANT-SERVICE"]
        instances = restaurant["snapshot"]

        # Case 2: look at each instance and check whether any of them works
        found_active_instance = False
        for instance in instances:
            status = instance["status"]
            print(f"[Analyze]: restaurant instance status: {status}")
            if status == "ACTIVE" or status == "BOOTING":
                found_active_instance = True

        if found_active_instance:
            return False

        print("[Analyze]: no active restaurant instance")
        return True


    def plan(self): # pyright: ignore[reportIncompatibleMethodOverride]
        return False
