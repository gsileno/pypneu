import unittest
import os
import sys

# Point to the new src directory
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from pypneu.parsers.PNLoader import parse_string

class ParsingTestCase(unittest.TestCase):

    def test_basic_declarations(self):
        """Tests parsing of simple place and transition declarations."""
        # Single place
        pn, errors = parse_string("b.")
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.places), 1)

        # Negative marking/place (Inhibitor or initial False)
        pn, errors = parse_string("~b.")
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.places), 1)

        # Multiple places (Comma separated)
        pn, errors = parse_string("b, c.")
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.places), 2)

        # Duplicate handling
        pn, errors = parse_string("b, b.")
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.places), 1)

    def test_place_to_transition_arcs(self):
        """Tests arcs from places to transitions using '->' syntax."""
        # Place to one transition
        pn, errors = parse_string("a -> #b.")
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.places), 1)
        self.assertEqual(len(pn.transitions), 1)
        self.assertEqual(len(pn.arcs), 1)

        # Place to multiple transitions (Fork)
        pn, errors = parse_string("a -> #b, #c.")
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.places), 1)
        self.assertEqual(len(pn.transitions), 2)
        self.assertEqual(len(pn.arcs), 2)

    def test_transition_to_place_arcs(self):
        """Tests arcs from transitions to places."""
        pn, errors = parse_string("#a -> b.")
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.places), 1)
        self.assertEqual(len(pn.transitions), 1)
        self.assertEqual(len(pn.arcs), 1)

    def test_reused_nodes(self):
        """Tests that the parser reuses existing nodes for the same IDs."""
        # One transition feeding two different places
        pn, errors = parse_string("#a -> c. #a -> b.")
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.places), 2)
        self.assertEqual(len(pn.transitions), 1)
        self.assertEqual(len(pn.arcs), 2)

        # Duplicate arc definition should be ignored or merged
        pn, errors = parse_string("#a -> c. #a -> b. #a -> b.")
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.places), 2)
        self.assertEqual(len(pn.transitions), 1)
        self.assertEqual(len(pn.arcs), 2)

    def test_transition_bindings_inference(self):
        """Tests logical bindings inferred from multi-input transitions."""
        # Independent transitions
        pn, errors = parse_string("a -> #b. c -> #b.")
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.places), 2)
        self.assertEqual(len(pn.transitions), 2)
        self.assertEqual(len(pn.arcs), 2)
        self.assertEqual(len(pn.t_bindings), 0)

        # Transition binding (Inferred from joint input 'a, c -> #b')
        pn, errors = parse_string("a -> #b. a, c -> #b.")
        self.assertEqual(errors, [])
        self.assertEqual(len(pn.places), 2)
        self.assertEqual(len(pn.transitions), 2)
        # Note: Depending on parser implementation, arc counts may vary
        # based on how bindings are linked.
        self.assertEqual(len(pn.t_bindings), 1)

    def test_parallel_operator_parsing(self):
        """Tests the 'PAR' keyword for parallel transition structures."""
        # Syntax: a -> PAR #b, #c.
        # This usually expands into multiple transitions with shared intermediate logic.
        pn, errors = parse_string("a -> PAR #b, #c.")
        self.assertEqual(errors, [])
        self.assertGreaterEqual(len(pn.places), 1)
        self.assertGreaterEqual(len(pn.transitions), 2)

if __name__ == '__main__':
    unittest.main()