import unittest
import os
import sys
import logging

# Ensure the library can be found in the src directory
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from pypneu.structures import (
    Place, Transition, Arc, PetriNetStructure, ArcType
)

# Set up logging for test transparency
logging.basicConfig(level=logging.DEBUG)


class TestPyPneuStructures(unittest.TestCase):
    def setUp(self):
        """Set up a basic net: P1 -> T1 -> P2"""
        self.p1 = Place(label="Input", marking=True)
        self.p2 = Place(label="Output", marking=False)
        self.t1 = Transition(label="Fire")

        # Direct Arc instantiation as per the new structures.py
        self.a1 = Arc(self.p1, self.t1, ArcType.ENABLER)
        self.a2 = Arc(self.t1, self.p2, ArcType.ENABLER)

        self.net = PetriNetStructure(
            places=[self.p1, self.p2],
            transitions=[self.t1],
            arcs=[self.a1, self.a2]
        )

    def test_id_assignment(self):
        """Verify that IDs are correctly prefixed and sequenced via _initialize_net."""
        self.assertEqual(self.p1.nid, "p1")
        self.assertEqual(self.p2.nid, "p2")
        self.assertEqual(self.t1.nid, "t1")
        self.assertEqual(self.a1.nid, "a1")
        self.assertEqual(self.a2.nid, "a2")

    def test_transition_enabling(self):
        """Test if transition correctly detects tokens and inhibitors."""
        self.assertTrue(self.t1.is_enabled())

        # Test disabling by removing token
        self.p1.marking = False
        self.assertFalse(self.t1.is_enabled())

    def test_atomic_firing_logic(self):
        """Verify tokens move using the new split consume/produce logic."""
        # Ensure p1 has token
        self.p1.marking = True

        # Phase 1: Consumption
        self.t1.consume_input_tokens()
        self.assertFalse(self.p1.marking, "Token should be removed from input")
        self.assertFalse(self.p2.marking, "Token should not be in output yet")

        # Phase 2: Production
        self.t1.produce_output_tokens()
        self.assertTrue(self.p2.marking, "Token should now be in output")

    def test_inhibitor_arc(self):
        """Test that an inhibitor arc prevents firing when a token is present."""
        p_inhibitor = Place(label="Inhibitor", marking=True)
        Arc(p_inhibitor, self.t1, ArcType.INHIBITOR)

        # Reset p1 to True to attempt a fire
        self.p1.marking = True

        # Should be disabled because inhibitor place has a token
        self.assertFalse(self.t1.is_enabled())

        # Clear inhibitor, should be enabled now
        p_inhibitor.marking = False
        self.assertTrue(self.t1.is_enabled())

    def test_is_source_logic(self):
        """Verify that a transition with no enabler inputs is identified as a source."""
        t_source = Transition(label="Source")
        p_out = Place(label="Out")
        Arc(t_source, p_out, ArcType.ENABLER)

        # No arcs go TO t_source, so it should be a source
        self.assertTrue(t_source.is_source)

        # However, our main t1 has an input from p1, so it is NOT a source
        self.assertFalse(self.t1.is_source)

    def test_source_firing_constraint(self):
        """Verify that firing increments the fired_count (used by Executor for 'max once')."""
        t_source = Transition(label="Source")
        self.assertEqual(t_source.fired_count, 0)

        # Fire the source
        t_source.consume_input_tokens()
        t_source.produce_output_tokens()

        self.assertEqual(t_source.fired_count, 1)

    def test_catalyst_biflow_logic(self):
        """Verify that a catalyst (In + Out arcs) preserves the token count."""
        p_cat = Place(label="Catalyst", marking=True)
        t_cat = Transition(label="UsesCatalyst")

        # Create Biflow
        Arc(p_cat, t_cat, ArcType.ENABLER)  # In
        Arc(t_cat, p_cat, ArcType.ENABLER)  # Out

        # Fire
        t_cat.consume_input_tokens()
        self.assertFalse(p_cat.marking, "Token temporarily removed during consumption")

        t_cat.produce_output_tokens()
        self.assertTrue(p_cat.marking, "Token restored during production")


if __name__ == "__main__":
    unittest.main()