import unittest
import pypneu
from pypneu.transformer import get_parser, PNTransformer
from pypneu.structures import ArcType, Place, Transition


class TestPNTransformer(unittest.TestCase):
    def setUp(self):
        self.parser = get_parser()
        self.transformer = PNTransformer()

    def test_basic_structure(self):
        """Verifies that a single statement generates the correct number of nodes."""
        code = "a, b : c -> d -o #t1 -> e."
        tree = self.parser.parse(code)
        net = self.transformer.transform(tree)

        # 6 unique places: a, b, c, d, e and the transition #t1
        self.assertEqual(len(net.places), 5)
        self.assertEqual(len(net.transitions), 1)
        self.assertEqual(len(net.arcs), 6)

    def test_inhibitor_assignment(self):
        """Ensures that the 3rd group in the DSL is correctly typed as INHIBITOR."""
        code = "a : b -> inhibitor_place -o #t1 -> c."
        tree = self.parser.parse(code)
        net = self.transformer.transform(tree)

        # Find the arc coming from 'inhibitor_place'
        inhibitor_arcs = [a for a in net.arcs if a.type == ArcType.INHIBITOR]

        self.assertEqual(len(inhibitor_arcs), 1)
        self.assertEqual(inhibitor_arcs[0].source.label, "inhibitor_place")
        self.assertEqual(inhibitor_arcs[0].target.label, "#t1")

    def test_unique_name_assumption(self):
        """Verifies that 'a' in two different statements refers to the same Place object."""
        code = """
        a : b -> c -o #t1 -> d.
        e : f -> g -o #t2 -> a.
        """
        tree = self.parser.parse(code)
        net = self.transformer.transform(tree)

        # Find the place labeled 'a'
        place_a = next(p for p in net.places if p.label == "a")

        # 'a' should be an input (as consumable) to t1 and an output to t2
        input_to_t1 = any(arc.source == place_a for arc in net.transitions[0].inputs)
        output_from_t2 = any(arc.target == place_a for arc in net.transitions[1].outputs)

        self.assertTrue(input_to_t1, "Place 'a' should be an input to transition 1")
        self.assertTrue(output_from_t2, "Place 'a' should be an output from transition 2")

        # Ensure 'a' isn't duplicated in the registry
        labels = [p.label for p in net.places]
        self.assertEqual(labels.count("a"), 1, "Place 'a' should only exist once in the net")

    def test_empty_lists(self):
        """Tests that the parser/transformer handles empty place lists correctly."""
        # A source transition with only outputs
        code = " : -> -o #source -> a."
        tree = self.parser.parse(code)
        net = self.transformer.transform(tree)

        t = net.transitions[0]
        self.assertTrue(t.is_source)
        self.assertEqual(len(t.outputs), 1)

    def test_bus_synchronization_registry(self):
        """Verifies that multiple statements with the same transition label are tracked."""
        code = """
        a : b -> c -o #shared -> d.
        e : f -> g -o #shared -> h.
        """
        tree = self.parser.parse(code)
        net = self.transformer.transform(tree)

        # Verify two transition nodes were created with the same label
        shared_transitions = [t for t in net.transitions if t.label == "#shared"]
        self.assertEqual(len(shared_transitions), 2)

if __name__ == "__main__":
    unittest.main()