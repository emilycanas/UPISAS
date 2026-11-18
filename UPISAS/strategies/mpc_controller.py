class MPCController:
    """One controller per service. Person A fills in the logic; this is the contract."""

    def __init__(self, service_name, max_response_time, min_availability):
        self.service_name = service_name
        self.max_response_time = max_response_time   # ms
        self.min_availability = min_availability     # 0..1
        # A: model, Kalman filter state, ... go here

    def decide(self, instances, current_weights, booting_count):
        """
        instances:       {instance_id: {"status", "request_rate", "response_time", "availability"}}
                         only ACTIVE instances (failed/missing ones are left out by B)
        current_weights: {instance_id: weight}   (may be empty: RAMSES default = equal split)
        booting_count:   number of instances added but not ACTIVE yet

        returns: {"instance_change": -1 | 0 | +1,
                  "weights": {instance_id: weight},   # ACTIVE instances only, sums to 1
                  "switch_to": None,                  # later: implementation name
                  "phase": str, # "learning" | "controlling"
                  "reason": str}
        """
        # Dummy: change nothing, equal split
        n = len(instances)
        weights = {iid: 1 / n for iid in instances} if n else {}
        return {"instance_change": 0, "weights": weights,
                "switch_to": None, "phase": "controlling", "reason": "dummy"}
