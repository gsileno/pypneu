import unittest
import os
import sys
import logging

# Ensure the src directory is in the path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from pypneu.transformer import parse_string
from pypneu.structures import ArcType

# Enable logging for parser/transformer debugging
logging.basicConfig(level=logging.DEBUG)


class ParsingTestCase(unittest.TestCase):

    def test_basic_declarations(self):
        """Tests parsing of simple place and transition declarations."""
        # Single place (factual statement)
        pn, errors = parse_string("b.")
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.places), 1)
        self.assertEqual(pn.places[0].label, "b")
        self.assertTrue(pn.places[0].marking)

        # Multiple places (Comma separated)
        pn, errors = parse_string("b, c.")
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.places), 2)

    def test_place_to_transition_arcs(self):
        """Tests arcs from places to transitions using '->' syntax."""
        # Standard consumption: a -> #b
        pn, errors = parse_string("a -> #b.")
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.places), 1)
        self.assertEqual(len(pn.transitions), 1)
        # Transition label should retain the #
        self.assertEqual(pn.transitions[0].label, "#b")
        self.assertEqual(len(pn.arcs), 1)
        self.assertEqual(pn.arcs[0].type, ArcType.ENABLER)

    def test_inhibitor_parsing(self):
        """Tests inhibitor arcs using the '-o' syntax."""
        # Note: Your grammar now supports skipping consumables: "-> a -o #b."
        pn, errors = parse_string("-> a -o #b.")
        self.assertEqual(errors, [])
        # We expect 1 arc from 'a' to '#b' of type INHIBITOR
        self.assertEqual(pn.arcs[0].type, ArcType.INHIBITOR)

    def test_catalyst_biflow_expansion(self):
        """Tests that catalysts (:) expand into two arcs (Biflow)."""
        # Syntax: a : c -> #b (a is consumed, c is a catalyst)
        pn, errors = parse_string("a : c -> #b.")
        self.assertEqual(errors, [])

        # Expected Arcs: 1 consumption (a) + 2 catalyst (c) = 3 total
        self.assertEqual(len(pn.arcs), 3)

        # Verify biflow for 'c'
        c_arcs = [a for a in pn.arcs if getattr(a.source, 'label', None) == 'c' or
                  getattr(a.target, 'label', None) == 'c']
        self.assertEqual(len(c_arcs), 2)

    def test_bus_synchronization_parsing(self):
        """Tests that multiple statements with the same #label create distinct transition nodes."""
        code = """
        p1 -> #sync.
        p2 -> #sync.
        """
        pn, errors = parse_string(code)
        self.assertEqual(errors, [])

        self.assertEqual(len(pn.transitions), 2)
        # Retaining the # as requested
        self.assertEqual(pn.transitions[0].label, "#sync")
        self.assertEqual(pn.transitions[1].label, "#sync")

    def test_reused_nodes(self):
        """Tests that the parser reuses existing Place nodes for the same IDs."""
        pn, errors = parse_string("a -> #t1. a -> #t2.")
        self.assertEqual(errors, [])

        self.assertEqual(len(pn.places), 1)
        self.assertEqual(len(pn.transitions), 2)
        # Check that the same 'a' object has two output arcs
        self.assertEqual(len(pn.places[0].outputs), 2)

    def test_complex_statement(self):
        """Tests a combined statement with consumables, catalysts, and inhibitors."""
        # a (cons) : c (cat) -> i (inhib) -o #fire -> out (output)
        code = "a : c -> i -o #fire -> out."
        pn, errors = parse_string(code)
        self.assertEqual(errors, [])

        # Arcs: 1(a) + 2(c biflow) + 1(i inhibitor) + 1(out) = 5
        self.assertEqual(len(pn.arcs), 5)

        t = pn.transitions[0]
        self.assertEqual(t.label, "#fire")

    def test_shorthand_omissions(self):
        """Tests that the grammar correctly handles omitted optional groups."""
        # Case: No consumables or catalysts, just an inhibitor and an output
        code = "-> i -o #only_inhib -> out."
        pn, errors = parse_string(code)
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.arcs), 2)  # 1 inhibitor + 1 output

        # Case: Just a transition and an output
        code = "-> #pure_source -> out."
        pn, errors = parse_string(code)
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.arcs), 1)


if __name__ == '__main__':
    unittest.main()