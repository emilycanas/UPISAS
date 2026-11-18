from UPISAS.strategy import Strategy
from datetime import datetime
import time


def totals(instance_snapshot):
    requests, ok, duration = 0, 0, 0.0
    endpoints = instance_snapshot.get("httpMetrics")
    if endpoints is None:
        return requests, ok, duration   #probe sent no metrics this round
    
    for endpoint in endpoints.values():
        for outcome in endpoint["outcomeMetrics"].values():
            requests += outcome["count"]
            duration += outcome["totalDuration"]
            if outcome["status"] < 500:
                ok += outcome["count"]
    
    return requests, ok, duration;




# UPISAS/strategies/mpc_strategy.py 
# In analyze(), monitor data.
# In plan(), decide what to do in the given scenario.

class MPCStrategy(Strategy):
    def __init__(self, exemplar):
        super().__init__(exemplar)
        self.last_add = None
        self.previous_totals = {}
        self.stats = {}

    def analyze(self): # pyright: ignore[reportIncompatibleMethodOverride]
        data = self.knowledge.monitored_data
        latest = data["services"][-1]

        seen = set()

        # Calculate delta_t (seconds between the two monitor timestamps)
        delta_t = None
        if len(data["timestamp"]) >= 2:
            now = datetime.fromisoformat(data["timestamp"][-1])
            before = datetime.fromisoformat(data["timestamp"][-2])
            delta_t = (now - before).total_seconds()


        # Step 1: get the every instance totals (nº of requests, nº of ok requests, time spent handing the requests) and stats (request rate, response time, availability)
        for service_name, service in latest.items():
            snapshot = service["snapshot"]
            if snapshot is None:
                seen.update(service["instances"])
                continue

            for instance in snapshot:
                instance_id = instance["instanceId"]
                seen.add(instance_id)
                new = totals(instance)
                old = self.previous_totals.get(instance_id)
                stats = self.stats.setdefault(instance_id, {"service": service_name})
                status = instance["status"]
                stats["status"] = status

                if status not in ("ACTIVE", "BOOTING"):
                    stats["request_rate"] = 0.0
                    continue    # failed: keep the old totals, metrics are empty

                if old is not None and delta_t:
                    d_requests = new[0] - old[0]
                    d_ok = new[1] - old[1]
                    d_duration = new[2] - old[2]
                    if d_requests < 0:
                        d_requests, d_ok, d_duration = new
                    if d_requests > 0:
                        stats["request_rate"] = d_requests / delta_t
                        stats["response_time"] = d_duration / d_requests
                        stats["availability"] = d_ok / d_requests
                    else:
                        stats["request_rate"] = 0.0

                self.previous_totals[instance_id] = new

        # Instances that disappear from the monitor data
        for instance_id, s in self.stats.items():
            if instance_id not in seen:
                s["status"] = "MISSING"
                s["request_rate"] = 0.0

        for instance_id, s in self.stats.items():
            if instance_id is "config-server":
                continue
            print(f"{s['service']:<24} {instance_id:<55} {s['status']:<12} "
                 f"{s.get('request_rate', 0):6.1f} req/s  "
                 f"{s.get('response_time', 0):7.1f} ms  "
                 f"{s.get('availability', 0):.2f}")
            print("-" * 40)

        return False


    def plan(self): # pyright: ignore[reportIncompatibleMethodOverride]
         # Don't add another instance if we added one less than 60 seconds ago
        if self.last_add is not None and time.monotonic() - self.last_add < 60:
            print("[Plan]: already started an instance, waiting for it to boot")
            return False

        self.knowledge.plan_data = {
            "operation": "addInstances",
            "parameters": {
                "serviceImplementationName": "restaurant-service",
                "numberOfInstances": 1,
            },
        }
        self.last_add = time.monotonic()
        print(f"[Plan]: starting a new restaurant-service instance")
        return True


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
                  "reason": str}
        """
        # Dummy: change nothing, equal split
        n = len(instances)
        weights = {iid: 1 / n for iid in instances} if n else {}
        return {"instance_change": 0, "weights": weights,
                "switch_to": None, "reason": "dummy"}
