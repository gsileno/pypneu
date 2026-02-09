import unittest
import os
import sys
import logging

# Adjusting path to point to the new src directory
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from pypneu.structures import Place, Transition, Arc, ArcType
from pypneu.executor import PetriNetExecution

# Enable logging to see the debug traces during test runs
logging.basicConfig(level=logging.DEBUG)


class TestPetriNetExecution(unittest.TestCase):

    def test_simulation_linear(self):
        """Simple Petri net: P1 -> T1 -> P2."""
        p1 = Place("p1", True)
        p2 = Place("p2")
        t1 = Transition("t1")

        # Direct Arc instantiation as per updated structures.py
        Arc(p1, t1, ArcType.ENABLER)
        Arc(t1, p2, ArcType.ENABLER)

        # The executor now automatically initializes the PetriNetStructure
        net = PetriNetExecution(places=[p1, p2], transitions=[t1])

        # Should complete 1 firing step
        self.assertEqual(net.run_simulation(iterations=10), 1)
        self.assertFalse(p1.marking)
        self.assertTrue(p2.marking)

    def test_simulation_source_transition(self):
        """Transition with no inputs (Source) triggered by a story."""
        p2 = Place("p2")
        t1 = Transition("t1")
        Arc(t1, p2, ArcType.ENABLER)

        # story=["t1"] ensures the source transition fires
        net = PetriNetExecution(places=[p2], transitions=[t1], story=["t1"])

        self.assertEqual(net.run_simulation(10), 1)
        self.assertTrue(p2.marking)

    def test_simulation_story_consumption(self):
        """Testing story sequence: T1 (Source) followed by T3."""
        t1 = Transition("t1")
        t2 = Transition("t2")
        t3 = Transition("t3")
        p2 = Place("p2")

        Arc(t1, p2, ArcType.ENABLER)
        Arc(p2, t2, ArcType.ENABLER)
        Arc(p2, t3, ArcType.ENABLER)

        # t3 should fire after t1 because it's requested in the story
        net = PetriNetExecution(places=[p2], transitions=[t1, t2, t3], story=["t1", "t3"])

        # Step 1: t1 fires (p2=True). Step 2: t3 fires (p2=False).
        self.assertEqual(net.run_simulation(10), 2)
        self.assertFalse(p2.marking)

    def test_simulation_bus_synchronization(self):
        """Verifies that two transitions with the same label fire as one bus."""
        p1 = Place("in1", True)
        p2 = Place("in2", True)
        p3 = Place("out1")
        p4 = Place("out2")

        # Two different transition objects with the same label
        t1 = Transition("shared_bus")
        t2 = Transition("shared_bus")

        Arc(p1, t1, ArcType.ENABLER)
        Arc(t1, p3, ArcType.ENABLER)
        Arc(p2, t2, ArcType.ENABLER)
        Arc(t2, p4, ArcType.ENABLER)

        net = PetriNetExecution(places=[p1, p2, p3, p4], transitions=[t1, t2])

        # Only 1 step should occur because they fire together
        steps = net.run_simulation(10)
        self.assertEqual(steps, 1)
        self.assertTrue(p3.marking)
        self.assertTrue(p4.marking)
        self.assertFalse(p1.marking)
        self.assertFalse(p2.marking)

    def test_inhibitor_logic(self):
        """Ensures inhibitor arcs prevent firing."""
        p_in = Place("input", True)
        p_block = Place("block", True)
        t1 = Transition("t1")

        Arc(p_in, t1, ArcType.ENABLER)
        Arc(p_block, t1, ArcType.INHIBITOR)

        net = PetriNetExecution(places=[p_in, p_block], transitions=[t1])

        # Should not fire because p_block has a token
        self.assertEqual(net.run_simulation(5), 0)
        self.assertTrue(p_in.marking)

    def test_catalyst_biflow_simulation(self):
        """Tests catalyst logic: token is required but not consumed."""
        p_cat = Place("catalyst", True)
        p_in = Place("input", True)
        t1 = Transition("t1")

        # Mimic what the transformer does for catalysts (Biflow)
        Arc(p_cat, t1, ArcType.ENABLER)  # Input
        Arc(t1, p_cat, ArcType.ENABLER)  # Output (Restore)
        Arc(p_in, t1, ArcType.ENABLER)  # Consumable

        net = PetriNetExecution(places=[p_cat, p_in], transitions=[t1])

        net.run_simulation(1)

        self.assertTrue(p_cat.marking, "Catalyst should still have token")
        self.assertFalse(p_in.marking, "Input should have been consumed")


if __name__ == '__main__':
    unittest.main()