import unittest
import os
import sys

# Adjusting path to point to the new src directory
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from pypneu.structures import Place, Transition, Arc, PlaceBinding, TransitionBinding
from pypneu.executor import PetriNetExecution


class PyProPneuTestCase(unittest.TestCase):

    def test_simulation_linear(self):
        """Simple Petri net: P1 -> T1 -> P2."""
        p1 = Place("p1", True)
        p2 = Place("p2")
        t1 = Transition("t1")

        # Using the refactored connect_to method
        p1.connect_to(t1)
        t1.connect_to(p2)

        net = PetriNetExecution(places=[p1, p2], transitions=[t1])
        net.init_control()

        # Should complete 1 firing step
        self.assertEqual(net.run_simulation(iterations=10), 1)
        self.assertFalse(p1.marking)
        self.assertTrue(p2.marking)

    def test_simulation_source_transition(self):
        """Transition with no inputs (Source) triggered by a story."""
        p2 = Place("p2")
        t1 = Transition("t1")
        t1.connect_to(p2)

        # story=["t1"] ensures the source transition fires
        net = PetriNetExecution(places=[p2], transitions=[t1], story=["t1"])
        net.init_control()

        self.assertEqual(net.run_simulation(10), 1)
        self.assertTrue(p2.marking)

    def test_simulation_story_consumption(self):
        """Testing story sequence: T1 (Source) followed by T3 (which fails if t2 is missing)."""
        t1 = Transition("t1")
        t2 = Transition("t2")
        t3 = Transition("t3")
        p2 = Place("p2")

        t1.connect_to(p2)
        p2.connect_to(t2)
        p2.connect_to(t3)

        # t3 should fire after t1 if it is enabled
        net = PetriNetExecution(places=[p2], transitions=[t1, t2, t3], story=["t1", "t3"])
        net.init_control()

        # Step 1: t1 fires (p2=True). Step 2: t3 fires (p2=False).
        self.assertEqual(net.run_simulation(10), 2)
        self.assertFalse(p2.marking)

    def test_simulation_fork_conflict(self):
        """Conflict resolution: P1 enables T1 and T2, only one should fire."""
        p1 = Place("p1", True)
        t1 = Transition("t1")
        t2 = Transition("t2")

        p1.connect_to(t1)
        p1.connect_to(t2)

        net = PetriNetExecution(places=[p1], transitions=[t1, t2])
        net.init_control()

        # Only 1 step is possible as p1 is consumed
        self.assertEqual(net.run_simulation(10), 1)
        self.assertFalse(p1.marking)

    def test_lppn_logic_propagation(self):
        """Complex test for Logic Programming Petri Net (LPPN) propagation."""
        p1 = Place("p1", True)
        p2 = Place("p2")
        p3 = Place("p3")
        p4 = Place("p4")
        p5 = Place("p5")

        bp1 = PlaceBinding()  # Logic Operator on Places
        bt1 = TransitionBinding()  # Logic Operator on Transitions

        t1 = Transition("t1")
        t2 = Transition("t2")

        # Physical Arcs
        p1.connect_to(t1)
        t1.connect_to(p2)
        t2.connect_to(p5)

        # Logic Arcs (Inference)
        p2.connect_to(bp1)
        p5.connect_to(bp1)
        bp1.connect_to(p4)  # (P2 AND P5) -> P4

        t1.connect_to(bt1)
        bt1.connect_to(t2)  # T1 -> T2

        net = PetriNetExecution(
            places=[p1, p2, p3, p4, p5],
            transitions=[t1, t2],
            p_bindings=[bp1],
            t_bindings=[bt1]
        )
        net.init_control()

        # Initial Markings
        self.assertTrue(p1.marking)
        self.assertFalse(p4.marking)

        # Execution
        # 1. t1 fires (because p1 is True)
        # 2. t1 -> bt1 -> t2 (t2 fires via inference)
        # 3. p2 and p5 are produced
        # 4. p2 AND p5 -> bp1 -> p4 (p4 is marked via inference)
        self.assertEqual(net.run_simulation(5), 1)

        self.assertFalse(p1.marking)
        self.assertTrue(p2.marking)
        self.assertTrue(p5.marking)
        self.assertTrue(p4.marking)


if __name__ == '__main__':
    unittest.main()