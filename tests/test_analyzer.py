import unittest
import os
import sys

# Ensure the src directory is in the path if not installed as a package
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from pypneu.structures import Place, Transition, Arc, PlaceBinding, TransitionBinding
from pypneu.analysis import PetriNetAnalysis
from pypneu.executor import PetriNetExecution


class AnalyzerTestCase(unittest.TestCase):

    def _setup_analysis(self, places=(), transitions=(), arcs=(), p_bindings=(), t_bindings=()):
        """Helper to inject the executor into the analysis engine."""
        executor = PetriNetExecution(
            places=places,
            transitions=transitions,
            arcs=arcs,
            p_bindings=p_bindings,
            t_bindings=t_bindings
        )
        return PetriNetAnalysis(executor)

    def test_serial_path_analysis(self):
        """Test a simple P1 -> T1 -> P2 -> T2 -> P3 sequence."""
        p1 = Place("p1", True)
        p2 = Place("p2")
        p3 = Place("p3")

        t1 = Transition("t1")
        t2 = Transition("t2")

        a1 = p1.connect_to(t1)
        a2 = t1.connect_to(p2)
        a3 = p2.connect_to(t2)
        a4 = t2.connect_to(p3)

        net = self._setup_analysis(
            places=[p1, p2, p3],
            transitions=[t1, t2],
            arcs=[a1, a2, a3, a4]
        )

        _, _, iterations = net.run_analysis()

        # Iterations usually equal steps to stability
        self.assertEqual(iterations, 2)
        # Check path base (Initial, after T1, after T2)
        self.assertEqual(len(net.path_base), 3)

    def test_nondeterministic_fork_analysis(self):
        """Test a fork where P1 enables both T1 and T2."""
        p1 = Place("p1", True)
        t1 = Transition("t1")
        t2 = Transition("t2")

        a1 = p1.connect_to(t1)
        a2 = p1.connect_to(t2)

        net = self._setup_analysis([p1], [t1, t2], [a1, a2])

        _, _, iterations = net.run_analysis()

        # State base should contain: Initial state, State after T1, State after T2
        # (Assuming T1 and T2 both consume P1)
        self.assertEqual(len(net.state_base), 3)
        self.assertEqual(len(net.path_base), 2)

    def test_logic_programming_bindings(self):
        """Test LPPN with Place and Transition bindings."""
        p1 = Place("p1", True)
        p2 = Place("p2")
        p3 = Place("p3")
        p4 = Place("p4")
        p5 = Place("p5")

        bp1 = PlaceBinding()
        bt1 = TransitionBinding()

        t1 = Transition("t1")
        t2 = Transition("t2")

        # Standard Petri Net arcs
        a1 = p1.connect_to(t1)
        a2 = t1.connect_to(p2)
        a8 = t2.connect_to(p5)

        # Logic Bindings (Inference)
        a3 = p2.connect_to(bp1)  # p2 is part of bp1 input
        a4 = p5.connect_to(bp1)  # p5 is part of bp1 input
        a5 = bp1.connect_to(p4)  # bp1 implies p4

        a6 = t1.connect_to(bt1)  # t1 enables bt1
        a7 = bt1.connect_to(t2)  # bt1 implies t2

        net = self._setup_analysis(
            places=[p1, p2, p3, p4, p5],
            transitions=[t1, t2],
            p_bindings=[bp1],
            t_bindings=[bt1],
            arcs=[a1, a2, a3, a4, a5, a6, a7, a8]
        )

        # Pre-execution check
        self.assertTrue(p1.marking)
        self.assertFalse(p4.marking)

        net.run_analysis()

        # Logic Check:
        # T1 fires -> produces P2.
        # T1 fires -> (Transition Binding) -> implies T2 fires.
        # T2 fires -> produces P5.
        # P2 AND P5 are now true -> (Place Binding) -> implies P4 is true.

        self.assertFalse(p1.marking)
        self.assertTrue(p2.marking)
        self.assertTrue(p5.marking)
        self.assertTrue(p4.marking)


if __name__ == '__main__':
    unittest.main()