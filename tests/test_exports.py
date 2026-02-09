import unittest
import os
import csv
import json
import tempfile
from src.pypneu.structures import Place, Transition, Arc, ArcType
from src.pypneu.executor import StochasticPetriNetExecution
from src.pypneu.simulator import BatchSimulator


class TestPypneuExports(unittest.TestCase):
    def setUp(self):
        """
        Set up a simple Linear Petri Net:
        (p1: label='ready', marking=True) -> [t1: label='produce'] -> (p2: label='buffer')
        """
        self.p1 = Place("ready", True)
        self.p2 = Place("buffer", False)
        self.t1 = Transition("produce")

        self.arcs = [
            Arc(self.p1, self.t1, ArcType.ENABLER),
            Arc(self.t1, self.p2, ArcType.ENABLER)
        ]

        self.net_params = {
            "places": [self.p1, self.p2],
            "transitions": [self.t1],
            "arcs": self.arcs
        }

    def test_executor_step_returns_list(self):
        """Verify that step() returns a List of Transitions for the simulator."""
        executor = StochasticPetriNetExecution(**self.net_params)
        fired_group = executor.step()

        self.assertIsNotNone(fired_group)
        self.assertIsInstance(fired_group, list)
        self.assertEqual(fired_group[0].label, "produce")

    def test_json_deduplication_logic(self):
        """
        Verify that multiple identical runs are compressed into a single path
        with an incremented count.
        """
        num_runs = 5
        simulator = BatchSimulator(StochasticPetriNetExecution, self.net_params)
        # iterations=1 means it will always do: s0 -> produce -> s1
        results = simulator.run_batch(n_runs=num_runs, iterations_per_run=1)

        json_data = results["json_data"]

        # Since the net is linear/deterministic, there should only be ONE unique path
        self.assertEqual(len(json_data["paths"]), 1, "Deterministic net should only produce 1 unique path.")
        self.assertEqual(json_data["counts"][0], num_runs, "The count should match the number of runs.")

        # Verify the path format: [state, transition, state]
        path = json_data["paths"][0]
        self.assertEqual(len(path), 3, "Path should be [s0, produce, s1]")
        self.assertEqual(path[1], "produce")

    def test_json_export_file_content(self):
        """Verify the physical JSON file structure matches the requested format."""
        simulator = BatchSimulator(StochasticPetriNetExecution, self.net_params)
        results = simulator.run_batch(n_runs=2, iterations_per_run=1)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            simulator.export_json(results["json_data"], tmp_path)

            with open(tmp_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # Check top-level keys
                self.assertIn("paths", data)
                self.assertIn("counts", data)
                self.assertIn("states", data)

                # Verify states dictionary isn't empty and contains lists of place names
                self.assertTrue(len(data["states"]) > 0)
                for state_id, places in data["states"].items():
                    self.assertIsInstance(places, list)
                    self.assertTrue(all(isinstance(p, str) for p in places))

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_csv_export_remains_flat(self):
        """Verify the CSV remains a flat event log (not deduplicated) for process mining."""
        num_runs = 3
        simulator = BatchSimulator(StochasticPetriNetExecution, self.net_params)
        results = simulator.run_batch(n_runs=num_runs, iterations_per_run=1)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            simulator.export_csv(results["event_logs"], tmp_path)
            with open(tmp_path, mode='r', encoding='utf-8') as f:
                rows = list(csv.DictReader(f))
                # 3 runs * 1 event = 3 rows
                self.assertEqual(len(rows), 3)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()