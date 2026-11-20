"""
Each round, per service:
  phase "learning"    : vary LB weights to collect data, add an instance if goals break
  phase "controlling" : try keep / add / remove, solve a QP (cvxpy) for each, pick cheapest

Model per instance (load L in req/s):   RT = a + b*L  (ms)    AV = c - d*L
decide() returns {"phase": "learning" | "controlling", "actions": [...]}.

MPC Overview:
Every round it:
  1. MEASURES  the system           -> update_models() gets the latest stats
  2. PREDICTS  the near future      -> a simple model per instance (see "Line")
  3. OPTIMISES over the next rounds -> _control_step() + _solve_qp()
  4. APPLIES only the first step    -> decide() returns this round's actions
and then repeats next round with fresh measurements ("receding horizon").

Two phases:
  learning     First rounds of every run. We don't have a model yet, so we
               collect data (load, response time, availability) per instance
               and vary the LB weights on purpose so instances see different
               loads. At the end, a straight line is fitted per instance
               (least squares).
  controlling  The rest of the run. The fitted lines are kept up to date with
               a Kalman filter, and decisions come from the optimisation.

The optimisation, in one sentence: for every option (keep / add one instance /
remove one instance) find the best LB weights for the next `horizon` rounds by
solving a convex Quadratic Program (QP), and pick the option with the lowest cost.
Trying every option and solving a QP for each is exact and simple; it avoids a
mixed-integer solver (instance counts are whole numbers, weights are not).

Legend:
  load L        requests per second one instance receives (= its weight x total load)
  RT            average response time (ms)
  AV            availability = share of requests that did NOT fail (status < 500)
  horizon N     how many rounds ahead the controller looks
  weights W     load-balancer weights: share of traffic per instance (sum = 1)
=============================================================================
"""
from dataclasses import dataclass
from typing import Optional
import copy
import numpy as np
import cvxpy as cp   # library for convex optimisation: we write the problem, it finds the optimum


@dataclass
class ServiceGoals:
    """The goals (thresholds) for one service. These are what the MPC optimises for."""
    max_response_time: float = 90.0   #stay below this
    min_availability: float = 0.99    #stay above this
    min_instances: int = 2
    max_instances: int = 5
    implementation: Optional[str] = None   # implementation name for addInstances (default: service name)


@dataclass
class MPCConfig:
    """Tuning knobs of the controller. The cost weights decide what the MPC
    cares about most when goals conflict (e.g. good RT vs. few instances)."""
    horizon: int = 5                   # rounds to look ahead
    boot_steps: int = 2                # rounds before a new instance takes traffic
    learning_rounds: int = 10          # length of the learning phase
    warmup_rounds: int = 3             # first rounds ignored for learning (JVM warm-up)
    excitation: float = 0.3            # extra weight on one instance while learning
    goal_weight: float = 100.0         # cost of breaking a goal
    change_weight: float = 1.0         # cost of changing LB weights
    instance_cost: float = 1.0         # cost per instance per round
    scaling_cost: float = 2.0          # one-off cost of add / remove
    max_load_per_instance: Optional[float] = None   # optional capacity cap (req/s)
    weight_threshold: float = 0.05     # only send weights that change more than this


# The model is one straight line, learned from data and kept up to date
class Line:
    """y = theta[0] + theta[1]*x, fitted by least squares, then tracked with a
    Kalman filter (parameters as a slowly drifting random walk).

    Used twice per instance:
      RT line:  response time = theta[0] + theta[1] * load    (theta = [a, b])
      AV line:  availability  = theta[0] + theta[1] * load    (theta = [c, -d])

    STEP 1 - least squares (at the end of learning, in __init__):
      np.polyfit(xs, ys, 1) finds the straight line that is closest to all
      learning samples (it minimises the sum of squared vertical distances).
      xs = loads, ys = measured response times (or availabilities).

    STEP 2 - Kalman filter (every round while controlling, in update()):
      A system changes over time (warm-up, other containers, deployments), so
      a line fitted once goes stale. The Kalman filter nudges theta with every
      new measurement. How far it nudges is decided automatically:
        P  how UNSURE we are about theta right now (a 2x2 covariance matrix).
           Large P = unsure = follow new measurements a lot.
        Q  how much theta may DRIFT per round (process noise). Adding Q to P
           every round stops the filter from becoming "too sure" and frozen.
        r  how NOISY one measurement is (measurement noise). Taken from how far
           the learning samples were from the fitted line.
      Each update is: "predict what we expect to measure, compare with what we
      did measure, move theta towards the difference by a gain k". The gain is
      big when P is big compared with r (we trust the data more than our
      line) and small when r is big (one noisy measurement shouldn't move us much).
      This is the textbook Kalman filter with the state = theta (the line's
      parameters) instead of a physical state; it is equivalent to recursive
      least squares with forgetting.
    """
    def __init__(self, xs, ys, default, default_noise):
        # Enough samples (>= 3) at different loads (ptp = max - min > 0)? Then fit a line.
        if len(xs) >= 3 and np.ptp(xs) > 0:
            slope, icpt = np.polyfit(xs, ys, 1)    # least-squares straight line
            if slope < 0:                          # e.g. still warming up: no load effect seen
                # A service shouldn't get FASTER under more load; a negative slope
                # means the data shows no real load effect, so use a flat line.
                slope, icpt = 0.0, float(np.mean(ys))
            self.theta = np.array([icpt, slope])
            # measurement noise r = variance of the errors around the fitted line
            self.r = max(np.var(np.array(ys) - (icpt + slope * np.array(xs))), 1e-6)
        else:
            # Not enough data: start from a default guess.
            self.theta, self.r = np.array(default, float), default_noise
        # Starting uncertainty P and drift Q, scaled to the noise level r so the
        # same settings work for RT (in ms, large numbers) and AV (0..1, small numbers).
        # The second entry (slope) is kept smaller: slopes are small numbers.
        self.P = np.diag([1.0, 0.01]) * self.r     # uncertainty of the parameters
        self.Q = np.diag([0.01, 0.0001]) * self.r  # how fast they may drift

    def update(self, x, y):                    # one Kalman step
        """New measurement: load x gave value y (e.g. 120 req/s gave 18 ms)."""
        h = np.array([1.0, x])                 # so that prediction = h @ theta = theta0 + theta1*x
        self.P += self.Q                       # PREDICT: parameters may have drifted -> less sure
        k = self.P @ h / (h @ self.P @ h + self.r)   # GAIN: how much to trust this measurement
        self.theta += k * (y - h @ self.theta)       # UPDATE: move towards (measured - predicted)
        self.P -= np.outer(k, h) @ self.P            # we just learned something -> more sure


# One option the controller considers (keep / add / remove X)
@dataclass
class Candidate:                               # one option evaluated by decide()
    kind: str                                  # "keep" | "add" | "remove"
    instance_id: Optional[str] = None          # which instance, for "remove"
    total_cost: float = float("inf")           # filled in by _solve_qp(); inf = impossible
    weights: Optional[dict] = None             # best LB weights for THIS round under this option
    predicted_rt: Optional[float] = None       # what the model expects this round (for logging)
    predicted_av: Optional[float] = None


class MPCController:
    def __init__(self, goals=None, config=None, managed_services=None):
        self.goals, self.cfg = goals or {}, config or MPCConfig()
        self.managed = set(managed_services) if managed_services else None   # None = all services
        self.phase, self.round = "learning", 0
        self.samples = {}        # instance -> [(load, rt, av)]   (learning phase)
        self.models = {}         # instance -> (rt Line, av Line) (controlling phase)
        self.service_model = {}  # service  -> (rt Line, av Line) for new instances
        self.service_of = {}     # instance -> service it belongs to
        self.last_report = {}    # service -> list of Candidates of the last round (for logging)

    def _managed(self, service):
        """Should the controller act on this service? Never on RAMSES' own config server."""
        return service.lower() != "config-server" and (
            self.managed is None or service in self.managed)

    # MODEL: learning the lines and keeping them up to date
    def update_models(self, stats):
        """Store samples (learning) or do a Kalman update (controlling).

        Called once per round by the strategy with the newest measurements:
        stats = {instance_id: {"service", "status", "request_rate",
                               "response_time", "availability"}}
        """
        self.round += 1
        for iid, s in stats.items():
            load, rt, av = s.get("request_rate") or 0, s.get("response_time"), s.get("availability")
            # Only use real measurements: managed service, instance active, it got traffic.
            if not self._managed(s["service"]) or s["status"] != "ACTIVE" or load <= 0 or rt is None:
                continue
            self.service_of[iid] = s["service"]
            if self.phase == "learning":
                # Learning: just collect (load, RT, AV) points for the least-squares fit later.
                if self.round > self.cfg.warmup_rounds:   # skip warm-up measurements
                    self.samples.setdefault(iid, []).append((load, rt, av))
            else:
                # Controlling: nudge this instance's lines towards the new measurement.
                m_rt, m_av = self._model(iid)
                m_rt.update(load, rt)
                if av is not None:
                    m_av.update(load, av)

    def _fit(self, points):
        """Fit both lines (RT and AV) from (load, rt, av) points.
        With no points, the defaults are used: RT = 50 ms + 1 ms per req/s, AV = 1.0."""
        rt_pts = [(L, rt) for L, rt, _ in points]
        av_pts = [(L, av) for L, _, av in points if av is not None]
        return (Line(*(zip(*rt_pts) if rt_pts else ([], [])), (50.0, 1.0), 100.0),
                Line(*(zip(*av_pts) if av_pts else ([], [])), (1.0, 0.0), 1e-3))

    def _finish_learning(self):
        """End of the learning phase: fit the lines and switch to controlling."""
        # One model per SERVICE, from all its instances' samples together.
        # New instances (added later) start with this one.
        for service in set(self.service_of.values()):
            pooled = [p for i, smp in self.samples.items() if self.service_of[i] == service for p in smp]
            self.service_model[service] = self._fit(pooled)
        # One model per INSTANCE (needs at least 5 samples, else defaults).
        for iid, smp in self.samples.items():
            self.models[iid] = self._fit(smp) if len(smp) >= 5 else self._fit([])
        self.phase = "controlling"

    def _model(self, iid, service=None):
        """Model of an instance. A new instance starts as a copy of its service model."""
        if iid == "new" or iid not in self.models:
            start = copy.deepcopy(self.service_model.get(service or self.service_of.get(iid))
                                  or self._fit([]))
            if iid == "new":
                return start                    # placeholder, not stored
            self.models[iid] = start
        return self.models[iid]


    # Decide() is the main entry point for the controller.
    # It is called once per round, with the latest stats and optional current weights and forecast.
    # It returns a dict with the current phase and a list of actions to take (add/remove instances, change weights).
    def decide(self, stats, current_weights=None, forecast=None):
        # Switch phase once the learning rounds are over.
        if self.phase == "learning" and self.round >= self.cfg.learning_rounds:
            self._finish_learning()
        actions = []
        # Every managed service is decided separately.
        for service in sorted({s["service"] for s in stats.values() if self._managed(s["service"])}):
            insts = {i: s for i, s in stats.items() if s["service"] == service and s["status"] != "MISSING"}
            weights = (current_weights or {}).get(service)
            step = self._learn_step if self.phase == "learning" else self._control_step
            actions += step(service, insts, weights, (forecast or {}).get(service))
        return {"phase": self.phase, "actions": actions}

    def _add(self, service, goals):
        """The action 'add one instance of this service'."""
        return {"type": "add", "service": service, "count": 1,
                "implementation": goals.implementation or service}

    # Learning phase: collect useful data, stay safe
    def _learn_step(self, service, insts, weights, _forecast):
        goals = self.goals.get(service, ServiceGoals())
        active = sorted(i for i, s in insts.items() if s["status"] == "ACTIVE")
        booting = any(s["status"] == "BOOTING" for s in insts.values())
        rts = [insts[i]["response_time"] for i in active if insts[i].get("response_time") is not None]
        broken = bool(rts) and np.mean(rts) > goals.max_response_time

        # Safety rule while there is no model yet: only add when there are too
        # few healthy instances (e.g. after a crash). Not for slow responses or
        # errors: more instances may not help, and every instance is a heavy container.
        actions = []
        healthy = len(active) + (1 if booting else 0)
        if healthy < goals.min_instances and not booting and len(insts) < goals.max_instances:
            actions.append(self._add(service, goals))

        # Excitation: to learn how RT depends on load, every instance must be seen
        # at DIFFERENT loads. So we cycle through weight patterns, each held for
        # 2 rounds (round // 2):
        #   pattern 0: equal split               e.g. 0.50 / 0.50
        #   pattern 1: extra weight on instance 1 e.g. 0.65 / 0.35
        #   pattern 2: extra weight on instance 2 e.g. 0.35 / 0.65   ... and repeat.
        # If RT is already too high ("broken"), we stay at the equal split.
        # This needs at least 2 active instances (with 1 there is nothing to shift).
        if len(active) >= 2:                                        # excitation
            m, focus = len(active), (self.round // 2) % (len(active) + 1)
            w = {i: 1 / m for i in active}
            if focus and not broken:
                w = {i: (1 - self.cfg.excitation) / m for i in active}
                w[active[focus - 1]] += self.cfg.excitation
            # only send if different from what is set now
            if any(abs(w[i] - (weights or {}).get(i, 0)) > 1e-3 for i in w):
                actions.append({"type": "weights", "service": service, "weights": w})
        return actions

    # Controlling phase: the MPC decision
    def _control_step(self, service, insts, weights, forecast):
        cfg, goals = self.cfg, self.goals.get(service, ServiceGoals())

        # Load forecast for the horizon: lam[t] = expected total req/s in round t.
        # Without a forecast: "it stays like now" for all N rounds (persistence forecast).
        load = sum(s.get("request_rate") or 0 for s in insts.values())
        lam = np.array((list(forecast) if forecast else []) + [load] * cfg.horizon)[:cfg.horizon]

        # round from which each instance can take traffic
        #   ACTIVE  -> 0 (now)    BOOTING -> 1 (next round)    failed etc. -> never (10**6)
        ready = {i: {"ACTIVE": 0, "BOOTING": 1}.get(s["status"], 10**6) for i, s in insts.items()}
        healthy = [i for i, r in ready.items() if r < 10**6]
        if not weights:                        # unknown current weights -> assume an equal split
            weights = {i: 1 / max(len(healthy), 1) for i in healthy}

        # The options (candidates) to compare:
        #   keep              - same instances
        #   add               - one more instance (if below max_instances)
        #   remove <instance> - one fewer, tried for EACH instance (if min_instances still holds)
        cands = [Candidate("keep")]
        if len(insts) < goals.max_instances:
            cands.append(Candidate("add"))
        cands += [Candidate("remove", i) for i in insts
                  if len([h for h in healthy if h != i]) >= goals.min_instances]
        if len(healthy) < goals.min_instances and len(cands) > 1 and cands[1].kind == "add":
            cands = [cands[1]]                     # too few instances: must add

        # Score every option: solve the QP for its set of instances.
        for c in cands:
            r = {i: x for i, x in ready.items() if i != c.instance_id}   # "remove": leave it out
            if c.kind == "add":
                r["new"] = cfg.boot_steps          # the new instance serves only after booting
            self._solve_qp(c, service, r, lam, weights, goals)

        # Pick the cheapest option. Only its FIRST round is used (receding horizon):
        # next round everything is solved again with new measurements.
        self.last_report[service] = cands
        best = min(cands, key=lambda c: c.total_cost)
        if best.total_cost == float("inf"):
            return []                              # no option possible: do nothing
        actions = []
        if best.kind == "add":
            actions.append(self._add(service, goals))
        if best.kind == "remove":
            actions.append({"type": "remove", "service": service, "instance_id": best.instance_id})
        # The option's weights for this round, for instances that can serve.
        # Only sent if some weight changes by more than weight_threshold (avoid tiny updates).
        new_w = {i: round(float(w), 4) for i, w in best.weights.items() if i != "new" and ready.get(i, 10**6) < 10**6}
        if new_w and max(abs(new_w.get(i, 0) - weights.get(i, 0)) for i in set(new_w) | set(weights)) > cfg.weight_threshold:
            actions.append({"type": "weights", "service": service, "weights": new_w})
        return actions

    # The QP - best LB weights over the horizon for one option
    def _solve_qp(self, cand, service, ready, lam, prev_weights, goals):
        """Best LB weights over the horizon for one fixed set of instances.

        Type of problem: a CONVEX QUADRATIC PROGRAM (QP).
          - "quadratic": the cost uses squares (e.g. weight^2, violation^2)
          - "convex": the cost is bowl-shaped, so there is exactly one best
            solution and the solver always finds it (no local optima).
        Solver: cvxpy rewrites the problem into a standard QP form and hands it
        to a solver it picks automatically. For a QP this is usually OSQP
        (an "operator splitting" / ADMM solver made for QPs); depending on your
        cvxpy version and installed solvers it may be another one, e.g. Clarabel.
        To see which one ran: problem.solver_stats.solver_name after solve().

        Decision variables (what the optimiser chooses):
          W[t, j] = LB weight of instance j in round t, for t = 0 .. N-1

        Predictions (the model), for every round t:
          load on instance j       = W[t, j] * lam[t]
          RT_j                     = a_j + b_j * load_j
          service RT  (weighted)   = sum_j W[t, j] * RT_j
                                   = W[t] @ a + lam[t] * (W[t]^2 @ b)
          service AV  (weighted)   = W[t] @ c - lam[t] * (W[t]^2 @ d)
          The W^2 term is what makes spreading load attractive: putting more
          weight on one instance raises its load AND the share of requests
          that see that load.

        Cost function (minimised; summed over all N rounds):
          goal_weight * violation^2 + 10 * violation    for RT and for AV
              violation = how far a goal is broken, as a fraction, 0 if met:
                RT: max(0, RT / max_RT - 1)               e.g. 10% too slow -> 0.1
                AV: max(0, (min_AV - AV) / (1 - min_AV))  e.g. 0.98 vs 0.99 -> 1.0
              Squared: big violations are VERY expensive.
              Linear (10x): small violations still cost something.
              These are "soft constraints": breaking a goal is allowed but
              expensive, so the problem can always be solved, even in overload.
          + change_weight * (W[t] - W[t-1])^2
              smooth changes, starting from the CURRENT weights (prev):
              no jumping traffic around ("move suppression").
          + 0.1 * RT / max_RT
              small tie-breaker: when all goals are met, still prefer faster.
          + 1000 * overload^2   (only if max_load_per_instance is set)
              penalty for giving an instance more req/s than its capacity.

        Rules (constraints):
          W >= 0, and every round's weights sum to 1 (all traffic goes somewhere)
          an instance that cannot serve yet (booting, failed) gets weight 0
          (a round where NO instance can serve has no sum-to-1 rule; it simply
          counts as availability 0, which the AV violation punishes heavily)

        After solving, the costs that don't depend on the weights are added:
          instance_cost * number of instances * N   (resources)
          scaling_cost                              (if this option adds/removes)
        That total is what decide() compares between the options.
        """
        cfg, N, names = self.cfg, self.cfg.horizon, list(ready)
        if not any(r < N for r in ready.values()):
            return                                    # nobody can serve traffic
        # Model coefficients for every instance in this option, as arrays:
        #   a, b: RT line (intercept, slope)      c, d: AV line (intercept, minus slope)
        params = [(*m_rt.theta, *m_av.theta) for m_rt, m_av in (self._model(i, service) for i in names)]
        a, b, c, d = (np.array(p) for p in zip(*params))
        # Clip to sensible values. b >= 0 and d >= 0 also keep the problem CONVEX
        # (otherwise the bowl could turn upside down and the solver would refuse).
        a, b, c, d = np.maximum(a, 0), np.maximum(b, 1e-6), np.clip(c, 0, 1), np.maximum(-d, 0)

        W = cp.Variable((N, len(names)), nonneg=True)  # weights per round and instance
        # not_ready[t, j] = 1 if instance j cannot serve in round t
        not_ready = np.array([[t < ready[i] for i in names] for t in range(N)], float)
        prev = np.array([[prev_weights.get(i, 0.0) for i in names]])   # current weights (row 0 of changes)

        # Predictions for all N rounds at once (vectors of length N)
        rt = W @ a + cp.multiply(lam, cp.square(W) @ b)       # predicted response time
        av = W @ c - cp.multiply(lam, cp.square(W) @ d)       # predicted availability
        # cp.pos(x) = max(0, x): only count the part where the goal is broken
        rt_violation = cp.pos(rt / goals.max_response_time - 1)
        av_violation = cp.pos((goals.min_availability - av) / max(1 - goals.min_availability, 1e-3))

        # The cost function (see the docstring above for each term)
        cost = (cfg.goal_weight * cp.sum_squares(rt_violation) + 10 * cp.sum(rt_violation)
                + cfg.goal_weight * cp.sum_squares(av_violation) + 10 * cp.sum(av_violation)
                + cfg.change_weight * cp.sum_squares(cp.diff(cp.vstack([prev, W]), axis=0))
                + 0.1 * cp.sum(rt) / goals.max_response_time)
        if cfg.max_load_per_instance:
            overload = cp.pos(cp.multiply(lam[:, None], W) - cfg.max_load_per_instance)
            cost += 1000 * cp.sum_squares(overload / cfg.max_load_per_instance)

        # Constraints: weights sum to 1 in rounds where someone can serve; 0 for not-ready instances
        serving = np.where(not_ready.min(axis=1) == 0)[0]   # rounds with >= 1 ready instance
        problem = cp.Problem(cp.Minimize(cost),
                             [cp.sum(W[serving], axis=1) == 1, cp.multiply(W, not_ready) == 0])
        problem.solve()                       # cvxpy finds the optimal W
        if problem.status not in ("optimal", "optimal_inaccurate"):
            return                            # no solution: this option stays at cost inf
        # Total cost of this option = QP cost + instances + scaling
        cand.total_cost = (problem.value + cfg.instance_cost * len(names) * N
                           + (cfg.scaling_cost if cand.kind != "keep" else 0))
        # Keep only the FIRST round's weights (receding horizon)
        w0 = np.clip(W.value[0], 0, None)          # weights for this round (all 0 if nobody is ready)
        cand.weights = dict(zip(names, w0 / w0.sum())) if w0.sum() > 0 else {}
        cand.predicted_rt, cand.predicted_av = float(rt.value[0]), float(av.value[0])