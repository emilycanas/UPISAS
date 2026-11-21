import csv
import os
import time
from datetime import datetime

COUNTED_SERVICES = ["ORDERING-SERVICE", "RESTAURANT-SERVICE",
                    "PAYMENT-PROXY-SERVICE", "DELIVERY-PROXY-SERVICE"]
MAX_RESPONSE_TIME = 800   # ms, ordering's goal in the utility

"""
Measures one run the same way for every strategy.
The runner calls record() after every monitor() and summary() at the end.
"""
class RunRecorder:

    def __init__(self, strategy_name, scenario_name, folder="results"):
        self.strategy_name = strategy_name
        self.scenario_name = scenario_name
        self.folder = folder
        self.start_time = time.monotonic()

        # One CSV file per run. The date and time in the name keep every run's
        # file unique, so a new run never overwrites an old one.
        os.makedirs(folder, exist_ok=True)
        date_and_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{strategy_name}_{scenario_name}_{date_and_time}.csv"
        self.file_path = os.path.join(folder, file_name)

        # The file stays open for the whole run; summary() closes it
        self.file = open(self.file_path, "w", newline="")
        self.writer = csv.writer(self.file)

        header = ["time_s", "requests", "successes", "availability", "response_time_ms"]
        for service_name in COUNTED_SERVICES:
            header.append("instances_" + service_name)
        self.writer.writerow(header)

        # The counters are cumulative, so we remember the previous values (and snapshot time) per instance to get this round's part
        self.previous_counters = {}     # instance_id -> (requests, successes, duration)
        self.previous_timestamp = {}    # instance_id -> timestamp of its last snapshot

        # Running totals for the summary at the end
        self.total_requests = 0
        self.total_successes = 0
        self.rounds_with_data = 0       # rounds that count for 'time within 800 ms' (with requests, or ordering up but no traffic)
        self.rounds_within_limit = 0    # of those, rounds with response time <= 800 ms
        self.total_instances = 0        # sum of all instance counts of all rounds
        self.rounds_recorded = 0
        self.traffic_started = False    # becomes True at the first round with requests
        

    """
    Requests, successes and duration of the successful requests of
    ordering since the last NEW snapshot of each of its instances.
    """
    def ordering_this_round(self, ordering_service):
        requests = 0
        successes = 0
        duration = 0.0
        new_snapshot = False   # True if at least one instance has a fresh snapshot

        if ordering_service is None or ordering_service["snapshot"] is None:
            return requests, successes, duration, new_snapshot   # no data this round

        for instance in ordering_service["snapshot"]:
            instance_id = instance["instanceId"]

            if self.previous_timestamp.get(instance_id) == instance["timestamp"]:
                continue
            new_snapshot = True   # this instance has a fresh snapshot

            # Add up the cumulative counters of this instance over all endpoints. Only successful requests (status < 500) count for the duration,
            # like in the naive strategy: failed requests are often fast and would make ordering look quicker than it is.
            new_requests = 0
            new_successes = 0
            new_duration = 0.0
            endpoints = instance.get("httpMetrics")
            if endpoints is not None:
                for endpoint in endpoints.values():
                    for outcome in endpoint["outcomeMetrics"].values():
                        new_requests += outcome["count"]
                        if outcome["status"] < 500:
                            new_successes += outcome["count"]
                            new_duration += outcome["totalDuration"]

            # This round's part = new counters minus the previous ones
            old_requests, old_successes, old_duration = self.previous_counters.get(instance_id, (0, 0, 0.0))
            delta_requests = new_requests - old_requests
            delta_successes = new_successes - old_successes
            delta_duration = new_duration - old_duration

            # A negative difference means the instance restarted and its counters began again from 0, so everything it counted is new
            if delta_requests < 0:
                delta_requests = new_requests
                delta_successes = new_successes
                delta_duration = new_duration

            # Remember for the next round
            self.previous_counters[instance_id] = (new_requests, new_successes, new_duration)
            self.previous_timestamp[instance_id] = instance["timestamp"]

            requests += delta_requests
            successes += delta_successes
            duration += delta_duration

        return requests, successes, duration, new_snapshot

    def record(self, monitored_data):
        latest = monitored_data["services"][-1]
        time_s = round(time.monotonic() - self.start_time, 1)

        requests, successes, duration, new_snapshot = self.ordering_this_round(latest.get("ORDERING-SERVICE"))

        availability = None
        if requests > 0:
            availability = successes / requests
        response_time = None 
        if successes > 0:
            response_time = duration / successes

        instance_counts = []
        for service_name in COUNTED_SERVICES:
            service = latest.get(service_name)
            if service is None:
                instance_counts.append(0)
            else:
                instance_counts.append(len(service["instances"]))

        row = [time_s, requests, successes, availability, response_time] + instance_counts
        self.writer.writerow(row)
        self.file.flush()   # write to disk now, so a crash does not lose the run

        self.total_requests += requests
        self.total_successes += successes
        if requests > 0:
            self.traffic_started = True
            self.rounds_with_data += 1
            # A round where every request failed has no response time:
            # it counts as a round with data, but not as within the limit
            if response_time is not None and response_time <= MAX_RESPONSE_TIME:
                self.rounds_within_limit += 1
        elif new_snapshot and self.traffic_started:
            # Ordering is up (its snapshot is new) but got no requests at all: they
            # never reached it, e.g. because no restaurant instance was running.
            # Ordering served nothing, so this round counts as outside the limit
            # instead of being skipped. Rounds before the load started don't count.
            self.rounds_with_data += 1
        for count in instance_counts:
            self.total_instances += count
        self.rounds_recorded += 1

    def summary(self):
        # Availability over the whole run: all successes / all requests. Not the average of rounds, so quiet rounds don't weigh as much as busy ones.
        availability = 0.0
        if self.total_requests > 0:
            availability = self.total_successes / self.total_requests

        time_within_limit = 0.0
        if self.rounds_with_data > 0:
            time_within_limit = self.rounds_within_limit / self.rounds_with_data

        average_instances = 0.0
        if self.rounds_recorded > 0:
            average_instances = self.total_instances / (self.rounds_recorded * len(COUNTED_SERVICES))

        # The utility of Code Challenge 2
        utility = (2 / 5 * availability
                   + 2 / 5 * time_within_limit
                   + 1 / 5 * (5 - average_instances) / 5)

        self.file.close()

        summary_path = os.path.join(self.folder, "summary.csv")
        new_file = not os.path.exists(summary_path)
        with open(summary_path, "a", newline="") as summary_file:
            writer = csv.writer(summary_file)
            if new_file:
                writer.writerow(["strategy", "scenario", "run_file", "availability",
                                 "time_within_800ms", "average_instances", "utility"])
            writer.writerow([self.strategy_name, self.scenario_name, os.path.basename(self.file_path),
                             round(availability, 4), round(time_within_limit, 4),
                             round(average_instances, 3), round(utility, 4)])

        print(f"Run summary ({self.strategy_name}, {self.scenario_name}): "
              f"availability {availability:.3f}, within 800 ms {time_within_limit:.3f}, "
              f"average instances {average_instances:.2f}, utility {utility:.4f}")

        return {"availability": availability, "time_within_800ms": time_within_limit,
                "average_instances": average_instances, "utility": utility}

