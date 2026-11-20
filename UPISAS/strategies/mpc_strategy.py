from UPISAS.strategy import Strategy
from datetime import datetime
import time
from UPISAS.strategies.mpc_controller import MPCController 


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


"""
The weights RAMSES is using now: what we last sent, or an equal split if we never sent any.
"""
def effective_weights(managed):
    if managed["weights"]:
        return managed["weights"]

    ids = list(managed["active"])

    # No active instances (e.g. right after a crash): there is nothing to split, and returning early also avoids dividing by zero below
    if not ids:
        return {}

    equal_share = 1 / len(ids)
    weights = {}
    for instance_id in ids:
        weights[instance_id] = equal_share
    return weights


"""
True if any instance's weight differs by more than the threshold.
"""
def weights_changed(old, new, threshold):
    for instance_id in set(old) | set(new):
        if abs(old.get(instance_id, 0.0) - new.get(instance_id, 0.0)) > threshold:
            return True
    return False


"""
Picks the instance to stop when the controller wants one instance less
"""
def instance_to_remove(managed, new_weights):
    chosen_id = None
    smallest_weight = None
    for instance_id in managed["active"]:
        weight = new_weights.get(instance_id, 0.0)
        if smallest_weight is None or weight < smallest_weight:
            chosen_id = instance_id
            smallest_weight = weight
    return chosen_id


"""
removeInstance needs the address and the port of the instance to remove
"""
def address_and_port(instance_id):
    after_at = instance_id.split("@")[1]
    address, port = after_at.rsplit(":", 1)
    return address, int(port)


"""
Removes one instance from the weights and spreads its share over the others
"""
def redistribute(weights, removed_id):
    remaining = {}
    for instance_id, weight in weights.items():
        if instance_id != removed_id:
            remaining[instance_id] = weight

    if not remaining:
        return {}

    total = sum(remaining.values())
    if total == 0:
        # All remaining weights are 0: fall back to an equal split
        equal_share = 1 / len(remaining)
        for instance_id in remaining:
            remaining[instance_id] = equal_share
        return remaining

    # Scale up so they add up to 1 again (e.g. 0.3 and 0.3 become 0.5 and 0.5)
    for instance_id in remaining:
        remaining[instance_id] = remaining[instance_id] / total
    return remaining


"""
UPISAS/strategies/mpc_strategy.py 
In analyze(), monitor data.
In plan(), decide what to do in the given scenario.
"""
class MPCStrategy(Strategy):
    def __init__(self, exemplar):
        super().__init__(exemplar)

        # Everything we know per instance, keyed by instance id:
        # {"service", "status", "request_rate", "response_time", "availability", "totals": (n requests, n ok requests, total duration in ms)}
        self.instances = {}

        # Everything we know per managed service, keyed by service ids. Goals come from RAMSES' qos_specification.json
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
                "implementation": None,     # e.g. "ordering-service", needed for addInstances
                "weights": {},              # {instance_id: weight} we last sent; empty = equal split
                "pending": [],              # times (time.monotonic()) we asked for a new instance
                "active": {},               # ACTIVE instances this round: {instance_id: instance}
                "booting_count": 0,         # pending + BOOTING instances
                "controller": MPCController(name, max_rt, min_avail),   # each service gets its own controller
            }

        # Seconds after which a requested instance that never appeared is forgotten
        self.pending_timeout = 90

        # Minimum change in any instance's weight before we send new weights
        self.weight_threshold = 0.05


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

        return not first_round 


    def plan(self): # pyright: ignore[reportIncompatibleMethodOverride]
        actions = []

        for (service_name, managed) in self.services.items():
            if managed["implementation"] is None:
                continue

            decision = managed["controller"].decide(managed["active"], managed["weights"], managed["booting_count"])
            print(f"Service: {service_name}; Decision phase: {decision['phase']}; Reason: {decision['reason']}")

            new_weights = dict(decision["weights"])

            # Add an instance
            if decision["instance_change"] > 0:
                actions.append((service_name, {
                    "operation": "addInstances",
                    "parameters": {"serviceImplementationName": managed["implementation"],
                                   "numberOfInstances": 1}}))

            # Remove an instance
            if decision["instance_change"] < 0 and len(managed["active"]) > 1:
                removed_id = instance_to_remove(managed, new_weights)
                address, port = address_and_port(removed_id)
                actions.append((service_name, {
                    "operation": "removeInstance",
                    "parameters": {"serviceImplementationName": managed["implementation"],
                                   "address": address, "port": port}}))

                # Its traffic must go to the remaining instances
                new_weights = redistribute(new_weights, removed_id)

            # Change the weights if they differ enough from the current ones
            if new_weights and weights_changed(effective_weights(managed), new_weights, self.weight_threshold):
                # Instances that still have a weight from earlier but are no longer used (e.g. crashed)
                no_longer_used = sorted(set(managed["weights"]) - set(new_weights))
                actions.append((service_name, {
                    "operation": "changeLBWeights",
                    "parameters": {"serviceId": service_name,
                                   "newWeights": new_weights,
                                   "instancesToRemoveWeightOf": no_longer_used}}))

        self.knowledge.plan_data = {"actions": actions} 
        for service_name, action in actions:
            print(f"[Plan]: {service_name}: {action['operation']} {action['parameters']}")
        return len(actions) > 0

        
        return False
