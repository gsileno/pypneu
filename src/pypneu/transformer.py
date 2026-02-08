import pathlib
from lark import Lark, Transformer, v_args
from pypneu.structures import PetriNetStructure, Place, Transition, Arc, ArcType


class PNTransformer(Transformer):
    def __init__(self, debug=True):
        super().__init__()
        self.debug = debug
        self.place_registry = {}  # UNA: unique places
        self.all_arcs = []
        self.all_transitions = []

    def _get_place(self, label):
        # Filter out empty matches from the Earley parser
        if not label or label == "None":
            return None
        if label not in self.place_registry:
            self.place_registry[label] = Place(label=label)
        return self.place_registry[label]

    def place_list(self, items):
        # Extract place objects, skipping any None results
        places = []
        for i in items:
            p = self._get_place(str(i))
            if p:
                places.append(p)
        return places

    @v_args(inline=True)
    def statement(self, consumables, catalysts, inhibitors, transition_token, outputs):
        t_label = str(transition_token)
        t_node = Transition(label=t_label)
        self.all_transitions.append(t_node)

        if self.debug:
            print(f"\n[DEBUG] Processing Statement for {t_label}")
            print(f"  - Consumables (In): {[p.label for p in consumables]}")
            print(f"  - Catalysts (In+Out): {[p.label for p in catalysts]}")
            print(f"  - Inhibitors (Block): {[p.label for p in inhibitors]}")
            print(f"  - Outputs (Out):    {[p.label for p in outputs]}")

        # 1. Consumables -> Standard ENABLER (Input)
        for p in consumables:
            self.all_arcs.append(Arc(p, t_node, ArcType.ENABLER))

        # 2. Catalysts -> BIFLOW (One Arc in, One Arc out)
        # This keeps the token count the same while requiring it to fire.
        for p in catalysts:
            # Input arc to check/consume
            self.all_arcs.append(Arc(p, t_node, ArcType.ENABLER))
            # Output arc to immediately restore
            self.all_arcs.append(Arc(t_node, p, ArcType.ENABLER))

        # 3. Inhibitors -> INHIBITOR (Input)
        for p in inhibitors:
            self.all_arcs.append(Arc(p, t_node, ArcType.INHIBITOR))

        # 4. Outputs -> Standard ENABLER (Output)
        for p in outputs:
            self.all_arcs.append(Arc(t_node, p, ArcType.ENABLER))

        return t_node

    def start(self, items):
        if self.debug:
            print(f"\n[DEBUG] Transformer Complete.")
            print(f"  Total Unique Places: {len(self.place_registry)}")
            print(f"  Total Transitions:   {len(self.all_transitions)}")
            print(f"  Total Arcs:          {len(self.all_arcs)}")

        return PetriNetStructure(
            places=list(self.place_registry.values()),
            transitions=self.all_transitions,
            arcs=self.all_arcs
        )


def get_parser():
    grammar_path = pathlib.Path(__file__).parent / "pn.lark"
    if not grammar_path.exists():
        raise FileNotFoundError(f"Missing grammar file at {grammar_path}")

    with open(grammar_path, "r", encoding="utf-8") as f:
        return Lark(f.read(), start='start', parser='earley')


if __name__ == "__main__":
    # Test case: a, b : c -> d -o #b -> e.
    # Expected arcs: 2 (cons) + 2 (cat loop) + 1 (inhib) + 1 (out) = 6
    code = "a, b : c -> d -o #b -> e."
    parser = get_parser()
    tree = parser.parse(code)
    net = PNTransformer(debug=True).transform(tree)
    print("\nGenerated Structure:")
    print(net)