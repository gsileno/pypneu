import csv
import io
from collections import Counter
from typing import List, Dict, Any


class BatchSimulator:
    def __init__(self, execution_class, net_params: Dict[str, Any]):
        """
        :param execution_class: The Executor class to use (e.g., StochasticPetriNetExecution)
        :param net_params: Dictionary containing 'places', 'transitions', and 'arcs'
        """
        self.execution_class = execution_class
        self.net_params = net_params

    def run_batch(self, n_runs: int, iterations_per_run: int = 100):
        paths = []
        final_markings = []
        event_logs = []

        for i in range(n_runs):
            # Instantiate a fresh executor for every run
            executor = self.execution_class(**self.net_params)

            # Setup a list to track this specific run's path
            current_path = []

            # Patch the fire_group method to log events for the CSV
            original_fire = executor._fire_group

            def logged_fire(transitions):
                for t in transitions:
                    event_type = t.label if t.label else "unlabeled"
                    current_path.append(event_type)
                    event_logs.append({
                        "run_id": i,
                        "step": len(current_path),
                        "event_type": event_type
                    })
                original_fire(transitions)

            executor._fire_group = logged_fire

            # Execute
            executor.run_simulation(iterations=iterations_per_run)

            paths.append(" -> ".join(current_path))
            final_markings.append(executor.pn.marking_to_string())

        return {
            "paths": paths,
            "marking_distribution": Counter(final_markings),
            "event_logs": event_logs
        }

    def export_csv(self, event_logs: List[Dict], filename: str = "event_log.csv"):
        with open(filename, mode='w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["run_id", "step", "event_type"])
            writer.writeheader()
            writer.writerows(event_logs)
        return filename