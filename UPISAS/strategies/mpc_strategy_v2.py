'''
Glue between UPISAS/RAMSES and the MPC Controller V2:
   analyze(): turn the cumulative counters from monitoring into per-instance
              request rate, response time and availability
   plan():    update the model, ask the MPC what to do, convert the decision
              into a RAMSES operation in knowledge.plan_data

 Every run starts in the "learning" phase (the controller varies LB weights to
 learn the model), then switches to "controlling" (MPC decisions).
 decide() returns {"phase": ..., "actions": [...]}; self.phase holds the phase.
'''

from UPISAS.strategy import Strategy
from UPISAS.strategies.mpc_controller import MPCController, MPCConfig, ServiceGoals
from UPISAS.strategies.mpc_logging import RunLogger
from contextlib import redirect_stdout
from datetime import datetime
import io
import time


GOALS = {
    "RESTAURANT-SERVICE": ServiceGoals(max_response_time=90.0, min_availability=0.95,min_instances=2, max_instances=5),
    # "ORDERING-SERVICE": ServiceGoals(max_response_time=90.0, min_availability=0.95,min_instances=2, max_instances=5),
    # "PAYMENT-PROXY-SERVICE": ServiceGoals(max_response_time=90.0, min_availability=0.95,min_instances=2, max_instances=5),
    # "DELIVERY-PROXY-SERVICE": ServiceGoals(max_response_time=90.0, min_availability=0.95,min_instances=2, max_instances=5),
}
MANAGED_SERVICES = list(GOALS)

CONFIG = MPCConfig(
    horizon=5,               # 5 rounds ahead
    boot_steps=2,            # TODO: measure this (B's actuator test) and set it here
    max_load_per_instance=None,   #TODO: set from a load test if the linear model is too optimistic
    learning_rounds=5,      # learning phase; with 5 s rounds + 3 warm-up
)

SCALE_COOLDOWN_S = 80


def totals(instance_snapshot):
    requests, ok, duration = 0, 0, 0.0
    endpoints = instance_snapshot.get("httpMetrics")
    if endpoints is None:
        return requests, ok, duration   # probe sent no metrics this round

    for endpoint in endpoints.values():
        for outcome in endpoint["outcomeMetrics"].values():
            requests += outcome["count"]
            duration += outcome["totalDuration"]
            if outcome["status"] < 500:
                ok += outcome["count"]

    return requests, ok, duration


def parse_address(instance_id):
    # RAMSSES instance ids look like 'restaurant-service@sefa-restaurant-service:58085'
    host_port = instance_id.split("@")[-1]
    address, port = host_port.rsplit(":", 1)
    return address, int(port)


def implementation_of(instance_id, fallback):
    # The part before '@' is the implementation id
    return instance_id.split("@")[0] or fallback


def normalized(weights):
    """Rounded weights that sum to exactly 1 (put the rounding error on the largest)."""
    total = sum(weights.values())
    if total <= 0:
        return dict(weights)
    w = {i: round(x / total, 4) for i, x in weights.items()}
    top = max(w, key=w.get)
    w[top] = round(w[top] + 1.0 - sum(w.values()), 4)
    return w


class MPCStrategy(Strategy):
    def __init__(self, exemplar):
        super().__init__(exemplar)
        self.previous_totals = {}
        self.stats = {}
        self.current_weights = {}     # {service: {instance_id: weight}} we last sent
        self.monitored_weights = {}   # {service: weights reported by RAMSES or None}
        self.implementations = {}     # {service: currentImplementationId}
        self.last_scale = {}          # {service: time of last add/remove} for the cooldown
        self.phase = "learning"
        self.controller = MPCController(goals=GOALS, config=CONFIG,managed_services=MANAGED_SERVICES)
        self.log = RunLogger()

    def analyze(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        data = self.knowledge.monitored_data
        latest = data["services"][-1]
        seen = set()
        fresh_data = False

        for service_name, service in latest.items():
            self.implementations[service_name] = service.get("currentImplementationId")
            config = service.get("instanceConfig") or {}
            self.monitored_weights[service_name] = config.get("loadBalancerWeights")

            snapshot = service["snapshot"]
            if snapshot is None:
                seen.update(service["instances"])
                continue

            for instance in snapshot:
                instance_id = instance["instanceId"]
                seen.add(instance_id)
                stats = self.stats.setdefault(instance_id, {"service": service_name})
                stats["status"] = instance["status"]
                stats["response_time"] = None    # None = no fresh measurement
                stats["availability"] = None

                if stats["status"] not in ("ACTIVE", "BOOTING"):
                    stats["request_rate"] = 0.0
                    continue    # failed: keep the old totals, metrics are empty

                # The probe refreshes a snapshot less often than UPISAS calls
                # monitor (in the logs: monitor every ~2 s, snapshot every ~11 s).
                # So compare with the previous *snapshot*, using its own timestamp.
                snap_ts = datetime.fromisoformat(instance["timestamp"])
                new = totals(instance)
                old = self.previous_totals.get(instance_id)   # (totals, timestamp)
                if old is not None and old[1] == snap_ts:
                    continue    # same snapshot as last round: keep last request_rate

                if old is not None:
                    delta_t = (snap_ts - old[1]).total_seconds()
                    d_requests = new[0] - old[0][0]
                    d_ok = new[1] - old[0][1]
                    d_duration = new[2] - old[0][2]
                    if d_requests < 0:        # counters reset (instance restarted)
                        d_requests, d_ok, d_duration = new
                    if delta_t > 0:
                        stats["request_rate"] = max(d_requests, 0) / delta_t
                        if d_requests > 0:
                            stats["response_time"] = d_duration / d_requests  # ms
                            stats["availability"] = d_ok / d_requests
                            fresh_data = True

                self.previous_totals[instance_id] = (new, snap_ts)

        # instances that disappeared
        for instance_id, s in self.stats.items():
            if instance_id not in seen:
                s.update(status="MISSING", request_rate=0.0,
                         response_time=None, availability=None)

        self.knowledge.analysis_data = self.stats

        # plan only when at least one instance has a new measurement,
        # so every controller round is based on new data
        if not fresh_data:
            self.log.log_round(self.stats, self._current_weights(), self.controller, new_data=False)
        return fresh_data

    def _current_weights(self):
        """Current LB weights per service, for the controller's change cost.
        The interface caches instanceConfig for up to 60 s, so right after a
        change RAMSES may still report the old weights. So: use what we sent
        last, as long as it covers the same instances; otherwise what RAMSES
        reports; otherwise nothing (the controller then assumes equal weights)."""
        result = {}
        for service in set(self.monitored_weights) | set(self.current_weights):
            alive = {i for i, s in self.stats.items()
                     if s["service"] == service and s["status"] in ("ACTIVE", "BOOTING")}
            sent = self.current_weights.get(service)
            if sent and set(sent) <= alive and any(i in sent for i in alive):
                result[service] = sent
            elif self.monitored_weights.get(service):
                result[service] = self.monitored_weights[service]
        return result

    def plan(self):  # pyright: ignore[reportIncompatibleMethodOverride]
        """Ask the controller and turn its actions into a list of RAMSES
        operations in knowledge.plan_data. execute() sends them one by one."""
        weights_now = self._current_weights()      # weights in effect during this round
        self.controller.update_models(self.stats)
        result = self.controller.decide(self.stats, current_weights=weights_now)
        self.phase, actions = result["phase"], result["actions"]

        operations, skipped = [], []
        for a in actions:
            if a["type"] in ("add", "remove"):
                # cooldown: no two add/remove actions for a service within SCALE_COOLDOWN_S
                last = self.last_scale.get(a["service"], -1e9)
                if time.monotonic() - last < SCALE_COOLDOWN_S:
                    skipped.append(a)
                    continue
                self.last_scale[a["service"]] = time.monotonic()
            if a["type"] == "weights":
                self.current_weights[a["service"]] = a["weights"]
            operations.append(self._to_ramses(a))

        self.log.log_round(self.stats, weights_now, self.controller, new_data=True,
                           actions=actions, operations=operations, skipped=skipped)
        if not operations:
            return False
        self.knowledge.plan_data = operations
        return True

    def execute(self, adaptation=None, **kwargs):  # pyright: ignore[reportIncompatibleMethodOverride]
        """The interface's /execute takes ONE operation per request, so send
        the planned operations one after the other through UPISAS.
        UPISAS calls this with extra options (e.g. with_validation=...);
        they are passed on unchanged for every operation."""
        operations = adaptation if adaptation is not None else self.knowledge.plan_data
        if isinstance(operations, dict):
            operations = [operations]
        ok = True
        for op in operations:
            self.knowledge.plan_data = op
            output = io.StringIO()
            with redirect_stdout(output):            # UPISAS prints every request ...
                result = super().execute(**kwargs)   # UPISAS sends knowledge.plan_data
            for line in output.getvalue().splitlines():
                if "posted configuration" not in line:   # ... keep only anything unusual
                    print(line)
            if result is False:
                print(f"!!   execute failed: {op['operation']}")
            ok = ok and result is not False
        self.knowledge.plan_data = operations
        return ok

    def _to_ramses(self, a):
        """Parameter names as the interface requires them (OPERATIONS in the
        UPISAS-RAMSES interface)."""
        if a["type"] == "add":
            impl = self.implementations.get(a["service"]) or a["implementation"].lower()
            return {"operation": "addInstances",
                    "parameters": {"serviceImplementationName": impl,
                                   "numberOfInstances": a["count"]}}
        if a["type"] == "remove":
            address, port = parse_address(a["instance_id"])
            return {"operation": "removeInstance",
                    "parameters": {
                        "serviceImplementationName":
                            implementation_of(a["instance_id"], a["service"]),
                        "address": address,
                        "port": port}}
        if a["type"] == "weights":
            # newWeights is keyed by the full instance id; instancesToRemoveWeightOf
            # is required by the interface, so it is always sent (here: empty)
            return {"operation": "changeLBWeights",
                    "parameters": {
                        "serviceId": a["service"],
                        "newWeights": normalized(a["weights"]),
                        "instancesToRemoveWeightOf": a.get("remove_weight_of", [])}}
        raise ValueError(f"unknown action {a}")