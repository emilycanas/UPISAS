"""
mpc_logging.py - readable console output + CSV logs for every round.

Console: one compact block per round
    === round 27 | t=135s | controlling ==============================
    service                inst  req/s   RT ms  avail  LB weights
    RESTAURANT-SERVICE      2/2  284.9    18.0  0.960  #37293=0.50 #34665=0.50
      #58085 MISSING
    ORDERING-SERVICE        1/1  337.9    74.5  0.990
    MPC  RESTAURANT-SERVICE: keep=4937  add=1988  -> add
    DO   addInstances restaurant-service

CSV files (in ./logs, one pair per run, written every round):
    run_<time>_services.csv   one row per service per round:
        round, t_s, phase, new_data, service, instances, active, booting, failed,
        request_rate, response_time_ms, availability, lb_weights,
        mpc_choice, mpc_costs, mpc_actions, sent_operations, skipped
        (actions are short text, e.g. "changeLBWeights RESTAURANT-SERVICE #37293=0.65 #58085=0.35")
    run_<time>_instances.csv  one row per instance per round:
        round, t_s, phase, service, instance, status, request_rate,
        response_time_ms, availability, lb_weight
"""
import csv
import json
import os
import time
from datetime import datetime

SKIP_SERVICES = ("config-server",)


def short(instance_id):
    """'restaurant-service@sefa-restaurant-service-37293:37293' -> '#37293' (the port)."""
    return "#" + instance_id.rsplit(":", 1)[-1]


def service_summary(instances):
    """Service-level numbers from its instances (RT and availability weighted by requests)."""
    status = [s["status"] for s in instances]
    rate = sum(s.get("request_rate") or 0 for s in instances)
    measured = [s for s in instances if s.get("response_time") is not None and s.get("request_rate")]
    w = sum(s["request_rate"] for s in measured)
    rt = sum(s["request_rate"] * s["response_time"] for s in measured) / w if w else None
    av = sum(s["request_rate"] * s["availability"] for s in measured) / w if w else None
    return {"instances": sum(st != "MISSING" for st in status),
            "active": status.count("ACTIVE"), "booting": status.count("BOOTING"),
            "failed": sum(st not in ("ACTIVE", "BOOTING", "MISSING") for st in status),
            "request_rate": rate, "response_time_ms": rt, "availability": av}


def fmt(x, digits):
    return "" if x is None else round(x, digits)


class RunLogger:
    def __init__(self, folder="logs"):
        os.makedirs(folder, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.start, self.round = time.monotonic(), 0
        self.history = []     # (t_s, service, summary) for the end-of-run summary
        self.ops_sent = []
        self.services_file = open(os.path.join(folder, f"run_{stamp}_services.csv"), "w", newline="")
        self.instances_file = open(os.path.join(folder, f"run_{stamp}_instances.csv"), "w", newline="")
        self.services_csv = csv.writer(self.services_file)
        self.instances_csv = csv.writer(self.instances_file)
        self.services_csv.writerow(
            ["round", "t_s", "phase", "new_data", "service", "instances", "active", "booting",
             "failed", "request_rate", "response_time_ms", "availability", "lb_weights",
             "mpc_choice", "mpc_costs", "mpc_actions", "sent_operations", "skipped"])
        self.instances_csv.writerow(
            ["round", "t_s", "phase", "service", "instance", "status", "request_rate",
             "response_time_ms", "availability", "lb_weight"])
        print(f"[log] writing {self.services_file.name} and {self.instances_file.name}")

    # one round
    def log_round(self, stats, weights, controller, new_data,
                  actions=(), operations=(), skipped=()):
        """Call once per round. weights = LB weights in effect during this round."""
        self.round += 1
        t = round(time.monotonic() - self.start)
        phase = controller.phase
        by_service = {}
        for iid, s in stats.items():
            if s["service"].lower() not in SKIP_SERVICES:
                by_service.setdefault(s["service"], {})[iid] = s

        if not new_data:
            print(f"--- round {self.round} | t={t}s | {phase} | no new monitoring data")

        else:
            print(f"\n=== round {self.round} | t={t}s | {phase} " + "=" * 30)
            print(f"{'service':<24}{'inst':>5}{'req/s':>8}{'RT ms':>8}{'avail':>7}  LB weights")

        for service in sorted(by_service):
            insts = by_service[service]
            summ = service_summary(list(insts.values()))
            w = (weights or {}).get(service) or {}
            choice, costs = self._decision(controller, service)
            mine = lambda xs: [x for x in xs if x.get("service") == service
                               or x.get("parameters", {}).get("serviceId") == service]
            self.history.append((t, service, summ))

            if new_data:
                rt = "" if summ["response_time_ms"] is None else f"{summ['response_time_ms']:.1f}"
                av = "" if summ["availability"] is None else f"{summ['availability']:.3f}"
                wtxt = " ".join(f"{short(i)}={x:.2f}" for i, x in w.items()) if w else ""
                print(f"{service:<24}{summ['active']:>3}/{summ['instances']:<1}"
                      f"{summ['request_rate']:>8.1f}{rt:>8}{av:>7}  {wtxt}")
                for iid, s in insts.items():
                    if s["status"] != "ACTIVE":
                        print(f"  {short(iid)} {s['status']}")

            self.services_csv.writerow(
                [self.round, t, phase, int(new_data), service, summ["instances"], summ["active"],
                 summ["booting"], summ["failed"], fmt(summ["request_rate"], 2),
                 fmt(summ["response_time_ms"], 2), fmt(summ["availability"], 4),
                 json.dumps({short(i): round(x, 4) for i, x in w.items()}) if w else "",
                 choice, costs,
                 "; ".join(self.describe_action(a) for a in mine(list(actions))),
                 "; ".join(self.describe(op) for op in mine(list(operations))),
                 "; ".join(self.describe_action(a) for a in mine(list(skipped)))])
            for iid, s in insts.items():
                self.instances_csv.writerow(
                    [self.round, t, phase, service, iid, s["status"], fmt(s.get("request_rate"), 2),
                     fmt(s.get("response_time"), 2), fmt(s.get("availability"), 4),
                     fmt(w.get(iid), 4) if w else ""])

        if new_data:
            self._print_decision(controller, operations, skipped)
        self.services_file.flush()
        self.instances_file.flush()

    def _decision(self, controller, service):
        if controller.phase == "learning":
            return "learning", ""
        cands = controller.last_report.get(service, [])
        if not cands:
            return "", ""
        best = min(cands, key=lambda c: c.total_cost)
        label = lambda c: c.kind + (short(c.instance_id) if c.instance_id else "")
        costs = " ".join(f"{label(c)}={'inf' if c.total_cost == float('inf') else round(c.total_cost)}"
                         for c in cands)
        return label(best), costs

    def _print_decision(self, controller, operations, skipped):
        if controller.phase == "learning":
            c = controller
            print(f"MPC  learning {c.round}/{c.cfg.learning_rounds} "
                  f"(samples: {sum(len(s) for s in c.samples.values())})")
        else:
            for service in controller.last_report:
                choice, costs = self._decision(controller, service)
                print(f"MPC  {service}: {costs}  -> {choice}")
        for op in operations:
            print(f"DO   {self.describe(op)}")
            self.ops_sent.append(op["operation"])
        for a in skipped:
            print(f"SKIP {a['type']} {a['service']} (cooldown)")
        if not operations and not skipped:
            print("DO   nothing")

    @staticmethod
    def describe_action(a):
        """Controller action -> short text, e.g. 'add', 'remove #37293', 'weights #1=0.50 #2=0.50'."""
        if a["type"] == "remove":
            return f"remove {short(a['instance_id'])}"
        if a["type"] == "weights":
            return "weights " + " ".join(f"{short(i)}={x:.2f}" for i, x in a["weights"].items())
        return a["type"]

    @staticmethod
    def describe(op):
        p = op["parameters"]
        if op["operation"] == "addInstances":
            return f"addInstances {p['serviceImplementationName']}"
        if op["operation"] == "removeInstance":
            return f"removeInstance {p['serviceImplementationName']} #{p['port']}"
        if op["operation"] == "changeLBWeights":
            w = " ".join(f"{short(i)}={x:.2f}" for i, x in p["newWeights"].items())
            return f"changeLBWeights {p['serviceId']} {w}"
        return str(op)

    # end of run
    def summary(self, services=("ORDERING-SERVICE", "RESTAURANT-SERVICE")):
        """Print the goals over the whole run and close the files."""
        print("\n=== run summary " + "=" * 45)
        for service in services:
            rows = [s for _, srv, s in self.history if srv == service]
            if not rows:
                continue
            serving = [s for s in rows if s["request_rate"] > 0 and (s["availability"] or 0) > 0]
            avs = [s["availability"] for s in rows if s["availability"] is not None]
            rts = [s["response_time_ms"] for s in rows if s["response_time_ms"] is not None]
            print(f"{service:<24} serving in {len(serving)}/{len(rows)} rounds "
                  f"({100 * len(serving) / len(rows):.0f}%)"
                  + (f", mean availability {sum(avs) / len(avs):.3f}" if avs else "")
                  + (f", mean RT {sum(rts) / len(rts):.1f} ms" if rts else ""))
        counts = {o: self.ops_sent.count(o) for o in sorted(set(self.ops_sent))}
        print(f"operations sent: {counts or 'none'}")
        print(f"logs: {self.services_file.name}, {self.instances_file.name}")
        self.services_file.close()
        self.instances_file.close()