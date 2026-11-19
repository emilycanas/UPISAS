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

        # Everything we know per instance, keyed by instance id:
        # {"service", "status", "request_rate", "response_time", "availability",
        #  "totals": (n requests, n ok requests, total duration in ms)}
        self.instances = {}

        # Everything we know per managed service, keyed by service id.
        # Goals come from RAMSES' qos_specification.json
        # (max_response_time in ms, min_availability as a fraction 0..1).
        self.services = {}
        goals = {"RESTAURANT-SERVICE": (90, 0.90),
                 "ORDERING-SERVICE": (800, 0.87),
                 "PAYMENT-PROXY-SERVICE": (500, 0.92),
                 "DELIVERY-PROXY-SERVICE": (500, 0.92)}
        for name, (max_rt, min_avail) in goals.items():
            self.services[name] = {
                "max_response_time": max_rt,
                "min_availability": min_avail,
                "implementation": None,   # e.g. "ordering-service", needed for addInstances
                "weights": {},            # {instance_id: weight} we last sent; empty = equal split
                "pending": [],            # times (time.monotonic()) we asked for a new instance
                "active": {},             # ACTIVE instances this round: {instance_id: instance}
                "booting_count": 0,       # pending + BOOTING instances
            }

        # Seconds after which a requested instance that never appeared is forgotten
        self.pending_timeout = 90


    def analyze(self): # pyright: ignore[reportIncompatibleMethodOverride]
        data = self.knowledge.monitored_data
        latest = data["services"][-1]
        first_round = len(data["timestamp"]) < 2

        seen = set()

        # Calculate delta_t (seconds between the two monitor timestamps)
        delta_t = None
        if not first_round:
            now = datetime.fromisoformat(data["timestamp"][-1])
            before = datetime.fromisoformat(data["timestamp"][-2])
            delta_t = (now - before).total_seconds()

        # Step 1: update every instance (totals and stats)
        for service_name, service in latest.items():
            managed = self.services.get(service_name)   # None for services we don't manage
            if managed is not None:
                managed["implementation"] = service["currentImplementationId"]

            snapshot = service["snapshot"]
            if snapshot is None:
                seen.update(service["instances"])
                continue

            for snap in snapshot:
                instance_id = snap["instanceId"]
                seen.add(instance_id)
                new = totals(snap)

                # A new instance appeared: if we asked for one, it has now arrived
                is_new = instance_id not in self.instances
                if is_new and not first_round:
                    print(f"[Analyze]: new instance detected: {instance_id}")
                    if managed is not None and managed["pending"]:
                        managed["pending"].pop(0)

                instance = self.instances.setdefault(instance_id, {"service": service_name})
                old = instance.get("totals")
                instance["status"] = snap["status"]

                if snap["status"] not in ("ACTIVE", "BOOTING"):
                    instance["request_rate"] = 0.0
                    continue    # failed: keep the old totals, metrics are empty

                if old is not None and delta_t:
                    d_requests = new[0] - old[0]
                    d_ok = new[1] - old[1]
                    d_duration = new[2] - old[2]

                    if d_requests < 0:
                        d_requests, d_ok, d_duration = new

                    if d_requests > 0:
                        instance["request_rate"] = d_requests / delta_t
                        instance["response_time"] = d_duration / d_requests
                        instance["availability"] = d_ok / d_requests
                    else:
                        instance["request_rate"] = 0.0

                instance["totals"] = new

        # Instances that disappeared from the monitor data
        for instance_id, instance in self.instances.items():
            if instance_id not in seen:
                instance["status"] = "MISSING"
                instance["request_rate"] = 0.0

        # Step 2: update every managed service (what the controller will need)
        now_mono = time.monotonic()
        for service_name, managed in self.services.items():
            # Forget requested instances that never appeared
            for requested_at in list(managed["pending"]):
                if now_mono - requested_at > self.pending_timeout:
                    managed["pending"].remove(requested_at)
                    print(f"[Analyze]: WARNING: instance for {service_name} never appeared")

            active = {}
            booting = 0
            for instance_id, instance in self.instances.items():
                if instance["service"] != service_name:
                    continue
                if instance["status"] == "ACTIVE":
                    active[instance_id] = instance
                elif instance["status"] == "BOOTING":
                    booting += 1

            managed["active"] = active
            managed["booting_count"] = booting + len(managed["pending"])

            print(f"{service_name:<24} impl={str(managed['implementation']):<26} "
                  f"active={len(active)}  booting={managed['booting_count']}  "
                  f"goals: <= {managed['max_response_time']} ms, >= {managed['min_availability']:.2f}")
        print("-" * 40)

        return False


    def plan(self): # pyright: ignore[reportIncompatibleMethodOverride]
        
        return False
