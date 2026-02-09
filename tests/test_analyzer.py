import unittest
import os
import sys
import logging

# Ensure the src directory is in the path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from pypneu.structures import Place, Transition, Arc, ArcType
from pypneu.analyzer import PetriNetAnalysis
from pypneu.executor import PetriNetExecution

# Enable logging for visibility during tests
logging.basicConfig(level=logging.DEBUG)


class AnalyzerTestCase(unittest.TestCase):

    def _setup_analysis(self, places=(), transitions=(), arcs=(), story=None):
        """Helper to inject the executor into the analysis engine."""
        executor = PetriNetExecution(
            places=places,
            transitions=transitions,
            arcs=arcs,
            story=story
        )
        return PetriNetAnalysis(executor)

    def test_serial_path_analysis(self):
        """Test a simple P1 -> T1 -> P2 -> T2 -> P3 sequence."""
        p1 = Place("p1", True)
        p2 = Place("p2")
        p3 = Place("p3")

        t1 = Transition("t1")
        t2 = Transition("t2")

        a1 = Arc(p1, t1, ArcType.ENABLER)
        a2 = Arc(t1, p2, ArcType.ENABLER)
        a3 = Arc(p2, t2, ArcType.ENABLER)
        a4 = Arc(t2, p3, ArcType.ENABLER)

        analysis = self._setup_analysis(
            places=[p1, p2, p3],
            transitions=[t1, t2],
            arcs=[a1, a2, a3, a4]
        )

        num_states, _, _ = analysis.run_analysis()

        # States: 1 (Initial), 2 (After T1), 3 (After T2)
        self.assertEqual(num_states, 3)
        self.assertEqual(len(analysis.state_base), 3)

        # Verify deadlocks (s2 should be a deadlock as P3 is a sink)
        deadlocks = analysis.get_deadlocks()
        self.assertEqual(len(deadlocks), 1)
        self.assertTrue(deadlocks[0].marking['p3'])

    def test_nondeterministic_fork_analysis(self):
        """Test a fork where P1 enables both T1 and T2 (Conflict)."""
        p1 = Place("p1", True)
        t1 = Transition("t1")
        t2 = Transition("t2")

        a1 = Arc(p1, t1, ArcType.ENABLER)
        a2 = Arc(p1, t2, ArcType.ENABLER)

        analysis = self._setup_analysis([p1], [t1, t2], [a1, a2])

        analysis.run_analysis()

        # State base should contain: s0 (P1), s1 (Empty via T1), s2 (Empty via T2)
        # Note: Since s1 and s2 have the same marking, they collapse into 2 unique states.
        self.assertEqual(len(analysis.state_base), 2)
        # However, the explorer should have found 2 distinct paths to explore
        self.assertEqual(len(analysis.path_base), 2)

    def test_bus_synchronization_analysis(self):
        """Verify the analyzer treats shared labels as a single atomic step."""
        p1 = Place("p1", True)
        p2 = Place("p2", True)
        t1 = Transition("shared")
        t2 = Transition("shared")

        a1 = Arc(p1, t1, ArcType.ENABLER)
        a2 = Arc(p2, t2, ArcType.ENABLER)

        analysis = self._setup_analysis([p1, p2], [t1, t2], [a1, a2])
        analysis.run_analysis()

        # Should only have 2 states: Initial and both consumed.
        # It should NOT explore firing T1 and T2 separately.
        self.assertEqual(len(analysis.state_base), 2)

    def test_source_firing_limit_analysis(self):
        """Ensure analyzer respects the 'fire once' rule for sources to avoid infinite loops."""
        p1 = Place("p1")
        t1 = Transition("source_t")  # No inputs
        Arc(t1, p1, ArcType.ENABLER)

        analysis = self._setup_analysis([p1], [t1], [])
        analysis.run_analysis()

        # State 0: p1: false, t1.fired=0
        # State 1: p1: true,  t1.fired=1
        # It should stop at State 1 because the source cannot fire again.
        self.assertEqual(len(analysis.state_base), 2)

    def test_inhibitor_reachability(self):
        """Test that inhibitor arcs correctly prune the state space."""
        p_in = Place("p_in", True)
        p_block = Place("p_block", True)
        t1 = Transition("t1")

        Arc(p_in, t1, ArcType.ENABLER)
        Arc(p_block, t1, ArcType.INHIBITOR)

        analysis = self._setup_analysis([p_in, p_block], [t1], [])
        analysis.run_analysis()

        # Should only have 1 state (Initial) because T1 is blocked
        self.assertEqual(len(analysis.state_base), 1)


if __name__ == '__main__':
    unittest.main()