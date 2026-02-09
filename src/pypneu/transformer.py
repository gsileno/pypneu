import pathlib
import logging
from lark import Lark, Transformer, Tree
from pypneu.structures import PetriNetStructure, Place, Transition, Arc, ArcType

logger = logging.getLogger("pypneu.transformer")


class PNTransformer(Transformer):
    def __init__(self):
        super().__init__()
        self.place_registry = {}
        self.all_arcs = []
        self.all_transitions = []

    def _get_place(self, label):
        if label not in self.place_registry:
            self.place_registry[label] = Place(label=label)
            logger.debug(f"[Registry] Created Place: {label}")
        return self.place_registry[label]

    def place_list(self, items):
        # items are tokens; returns a list of Place objects
        return [self._get_place(str(i)) for i in items]

    def mechanism(self, children):
        consumables, catalysts, inhibitors, outputs = [], [], [], []
        t_label = "unknown"

        for child in children:
            if isinstance(child, Tree):
                # Extract results from the aliased Tree
                # If the slot was empty (e.g., ": ->"), child.children[0] is None
                data = child.children[0] if child.children and child.children[0] is not None else []

                if child.data == 'consumables':
                    consumables = data
                elif child.data == 'catalysts':
                    catalysts = data
                elif child.data == 'inhibitors':
                    inhibitors = data
                elif child.data == 'outputs':
                    outputs = data
            elif child is not None:
                t_label = str(child)

        logger.info(
            f"[Transform] Processing {t_label} (Cons:{len(consumables)}, Cat:{len(catalysts)}, Inh:{len(inhibitors)}, Out:{len(outputs)})")

        t_node = Transition(label=t_label)
        self.all_transitions.append(t_node)

        # Map Arcs
        for p in consumables:
            self.all_arcs.append(Arc(p, t_node, ArcType.ENABLER))
            logger.debug(f"  {p.label} -> {t_label} (Consume)")

        for p in catalysts:
            self.all_arcs.append(Arc(p, t_node, ArcType.ENABLER))
            self.all_arcs.append(Arc(t_node, p, ArcType.ENABLER))
            logger.debug(f"  {p.label} <-> {t_label} (Catalyst)")

        for p in inhibitors:
            self.all_arcs.append(Arc(p, t_node, ArcType.INHIBITOR))
            logger.debug(f"  {p.label} -o {t_label} (Inhibit)")

        for p in outputs:
            self.all_arcs.append(Arc(t_node, p, ArcType.ENABLER))
            logger.debug(f"  {t_label} -> {p.label} (Produce)")

        return t_node

    def factual(self, children):
        places = children[0] if children else []
        for p in places:
            p.marking = True
            logger.info(f"[Factual] {p.label} marked active")
        return places

    def statement(self, children):
        return children[0]

    def start(self, items):
        net = PetriNetStructure(
            places=list(self.place_registry.values()),
            transitions=self.all_transitions,
            arcs=self.all_arcs
        )
        logger.info(f"[Summary] Petri Net built: {len(net.places)} Places, {len(net.arcs)} Arcs")
        return net


def get_parser():
    grammar_path = pathlib.Path(__file__).parent / "pn.lark"
    with open(grammar_path, "r", encoding="utf-8") as f:
        return Lark(f.read(), start='start', parser='earley')


def parse_string(code: str):
    parser = get_parser()
    try:
        tree = parser.parse(code)
        net = PNTransformer().transform(tree)
        return net, []
    except Exception as e:
        logger.error(f"Transformation failed: {e}")
        return None, [str(e)]


def compile_file(filepath: str):
    """
    Reads a .pneu file and returns a dictionary of net components ready for execution
    """
    path = pathlib.Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(path, 'r', encoding='utf-8') as f:
        code = f.read()

    return compile_string(code)


def compile_string(code: str):
    """
    Reads a string containing pneu code and returns a dictionary of net components ready for execution
    """
    net, errors = parse_string(code)

    if errors:
        raise ValueError(f"Parsing errors: {', '.join(errors)}")

    # The Executor expects a dict to unpack via **net_data
    return {
        "places": net.places,
        "transitions": net.transitions,
        "arcs": net.arcs
    }
