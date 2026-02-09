import unittest
import os
import csv
import tempfile
from src.pypneu.structures import Place, Transition, Arc, ArcType
from src.pypneu.executor import StochasticPetriNetExecution
from src.pypneu.simulator import BatchSimulator


class TestPypneuExports(unittest.TestCase):
    def setUp(self):
        """
        Set up a simple Linear Petri Net based on structures.py:
        (p1: label='ready', marking=True) -> [t1: label='produce'] -> (p2: label='buffer')
        """
        # Place(label, marking)
        self.p1 = Place("ready", True)
        self.p2 = Place("buffer", False)

        # Transition(label)
        self.t1 = Transition("produce")

        # Arc(source, target, type)
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

        # Check initial marking string
        self.assertIn("ready: ●", executor.pn.marking_to_string())

        fired_group = executor.step()

        self.assertIsNotNone(fired_group, "Transition should have fired.")
        self.assertIsInstance(fired_group, list, "Executor must return a list of fired transitions.")
        self.assertEqual(fired_group[0].label, "produce")

        # Verify token moved
        self.assertIn("ready: ○", executor.pn.marking_to_string())
        self.assertIn("buffer: ●", executor.pn.marking_to_string())

    def test_batch_simulator_aggregates_all_runs(self):
        """Verify that 10 runs produce 10 unique run_ids in the event log."""
        num_runs = 10
        simulator = BatchSimulator(StochasticPetriNetExecution, self.net_params)
        results = simulator.run_batch(n_runs=num_runs, iterations_per_run=5)

        event_logs = results["event_logs"]

        # Ensure we captured events
        self.assertTrue(len(event_logs) > 0, "No events were logged.")

        # Extract unique run_ids to ensure no overwriting happened
        unique_run_ids = set(log["run_id"] for log in event_logs)
        self.assertEqual(len(unique_run_ids), num_runs,
                         f"Expected {num_runs} unique run IDs, but found {len(unique_run_ids)}.")

    def test_csv_export_format(self):
        """Verify the CSV output contains the correct headers and multi-run data."""
        num_runs = 3
        simulator = BatchSimulator(StochasticPetriNetExecution, self.net_params)
        results = simulator.run_batch(n_runs=num_runs, iterations_per_run=1)

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            simulator.export_csv(results["event_logs"], tmp_path)

            with open(tmp_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

                # Check headers match the simulator requirements
                self.assertEqual(reader.fieldnames, ["run_id", "step", "event_type"])

                # Check that we have one 'produce' event per run
                self.assertEqual(len(rows), num_runs)
                self.assertEqual(rows[0]["event_type"], "produce")

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


if __name__ == "__main__":
    unittest.main()