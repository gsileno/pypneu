import unittest
import os
import sys

# Ensure the library can be found in the src directory
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from pypneu.structures import (
    Place, Transition, PetriNetStructure,
    ArcType, PlaceBinding, TransitionBinding
)


class TestPyPneu(unittest.TestCase):
    def setUp(self):
        """Set up a basic net: P1 -> T1 -> P2"""
        # We manually reset IDs for test predictability if your
        # class uses a global counter.
        Place._count = 1
        Transition._count = 1

        self.p1 = Place(label="Input", marking=True)
        self.p2 = Place(label="Output", marking=False)
        self.t1 = Transition(label="Fire")

        # Fluent API connections
        self.a1 = self.p1.connect_to(self.t1)
        self.a2 = self.t1.connect_to(self.p2)

        self.net = PetriNetStructure(
            places=[self.p1, self.p2],
            transitions=[self.t1]
        )

    def test_id_assignment(self):
        """Verify that IDs are correctly prefixed and sequenced."""
        self.assertEqual(self.p1.nid, "p1")
        self.assertEqual(self.p2.nid, "p2")
        self.assertEqual(self.t1.nid, "t1")
        # Arc IDs are generated during the connect_to call
        self.assertEqual(self.a1.nid, "a1")

    def test_transition_enabling(self):
        """Test if transition correctly detects tokens."""
        self.assertTrue(self.t1.is_enabled())

        self.p1.marking = False
        self.assertFalse(self.t1.is_enabled())

    def test_firing_logic(self):
        """Verify tokens move from source to target."""
        self.t1.fire()
        self.assertFalse(self.p1.marking)
        self.assertTrue(self.p2.marking)

    def test_inhibitor_arc(self):
        """Test that an inhibitor arc prevents firing when a token is present."""

        p_inhibitor = Place(label="Inhibitor", marking=True)
        # Using the ArcType enum for logic control
        p_inhibitor.connect_to(self.t1, type=ArcType.INHIBITOR)

        # Reset p1 to True to attempt a fire
        self.p1.marking = True

        # Should be disabled because inhibitor place 'p3' has a token
        self.assertFalse(self.t1.is_enabled())

        # Clear inhibitor, should be enabled now
        p_inhibitor.marking = False
        self.assertTrue(self.t1.is_enabled())

    def test_asp_generation(self):
        """Check if ASP logic strings are formatted correctly for Clingo."""

        pb = PlaceBinding()
        self.p1.connect_to(pb)
        pb.connect_to(self.p2)

        self.net.p_bindings = [pb]
        # net._initialize_net() updates the id2place maps and resets solver logic
        self.net._initialize_net()

        # Generate logic code (Assuming generate_asp_code or p_code method)
        asp = self.net.p_code()
        # Verify the material implication is present in the ASP string
        self.assertIn("p2 :- p1.", asp.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()