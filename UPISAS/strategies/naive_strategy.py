import time

from UPISAS.strategy import Strategy

# Baseline strategy: the "naive UPISAS" from RAMSES Code Challenge #2 (teaching team),
# copied unchanged. It follows RAMSES's own add-instance rules: when a service loses an
# instance, has no ACTIVE instance, or breaks its availability or response-time goal
# for 2 rounds in a row, it adds one instance (30 s cooldown, at most 4 per service).
# Do not change it: it must stay identical to the reference used for grading.

LIMITS = {
    "RESTAURANT-SERVICE": {"min_availability": 0.9, "max_response_time": 90},
    "ORDERING-SERVICE": {"min_availability": 0.87, "max_response_time": 800},
    "PAYMENT-PROXY-SERVICE": {"min_availability": 0.92, "max_response_time": 500},
    "DELIVERY-PROXY-SERVICE": {"min_availability": 0.92, "max_response_time": 500},
}
PERSISTENCE = 2
COOLDOWN_S = 30
MAX_ADDED_PER_SERVICE = 4
MIN_REQUESTS = 5


def counters(service):
    result = {}
    for instance in (service or {}).get("snapshot") or []:
        requests = failures = duration = 0
        for metric in (instance.get("httpMetrics") or {}).values():
            for outcome in (metric.get("outcomeMetrics") or {}).values():
                requests += outcome["count"]
                if outcome["status"] >= 500:
                    failures += outcome["count"]
                else:
                    duration += outcome.get("totalDuration") or 0
        result[instance["instanceId"]] = (requests, failures, duration)
    return result


def window(previous, current):
    before = counters(previous)
    requests = failures = duration = 0
    for instance_id, (r, f, d) in counters(current).items():
        r0, f0, d0 = before.get(instance_id, (0, 0, 0))
        if r < r0:
            r0, f0, d0 = 0, 0, 0
        requests, failures, duration = requests + r - r0, failures + f - f0, duration + d - d0
    successes = requests - failures
    return {"requests": requests,
            "availability": successes / requests if requests else None,
            "response_time": duration / successes if successes else None}


def has_active_instance(service):
    return any(i.get("status") == "ACTIVE" and not i.get("failed") and not i.get("unreachable")
               for i in service.get("snapshot") or [])


class NaiveStrategy(Strategy):
    def __init__(self, exemplar):
        super().__init__(exemplar)
        self.most_instances = {}
        self.violations = {}
        self.last_added = {}
        self.added = {}
        self.problems = []

    def problem(self, name, history):
        current = history[-1].get(name)
        previous = history[-2].get(name) if len(history) > 1 else None
        if current is None:
            return None
        count = len(current["instances"])
        most = self.most_instances.get(name, 0)
        self.most_instances[name] = max(most, count)
        if count < most:
            self.most_instances[name] = count
            return f"instances {most} -> {count}"
        if not has_active_instance(current):
            return "no ACTIVE instance"
        if previous is None:
            return None
        w = window(previous, current)
        limits = LIMITS.get(name)
        reason = None
        if limits and w["requests"] >= MIN_REQUESTS:
            if w["availability"] is not None and w["availability"] < limits["min_availability"]:
                reason = f"availability {w['availability']:.2f}"
            elif w["response_time"] is not None and w["response_time"] > limits["max_response_time"]:
                reason = f"response time {w['response_time']:.0f} ms"
        self.violations[name] = self.violations.get(name, 0) + 1 if reason else 0
        return reason if self.violations[name] >= PERSISTENCE else None

    def analyze(self):
        history = self.knowledge.monitored_data["services"]
        now = time.monotonic()
        self.problems = []
        for name in history[-1]:
            reason = self.problem(name, history)
            if (reason and now - self.last_added.get(name, -COOLDOWN_S) >= COOLDOWN_S
                    and self.added.get(name, 0) < MAX_ADDED_PER_SERVICE):
                self.problems.append((name, reason))
        return bool(self.problems)

    def plan(self):
        name, reason = self.problems[0]
        implementation = self.knowledge.monitored_data["services"][-1][name]["currentImplementationId"]
        self.knowledge.plan_data = {"operation": "addInstances",
                                    "parameters": {"serviceImplementationName": implementation,
                                                   "numberOfInstances": 1}}
        self.knowledge.analysis_data = {"service": name, "reason": reason}
        self.last_added[name] = time.monotonic()
        self.added[name] = self.added.get(name, 0) + 1
        self.violations[name] = 0
        return True

