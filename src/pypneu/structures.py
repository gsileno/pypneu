from enum import IntEnum, auto
from typing import List, Optional, Union, Dict


class ArcType(IntEnum):
    """Specifies the type of dependency between two nodes."""
    ENABLER = auto()    # Standard flow
    INHIBITOR = auto()  # Blocks target if source has token
    RESET = auto()      # Flushes target place


class Node:
    """Base class for all network elements."""

    def __init__(self, snid: Optional[str] = None):
        self.inputs: List['Arc'] = []
        self.outputs: List['Arc'] = []
        self.nid: Optional[str] = None  # Net-level ID
        self.snid: Optional[str] = snid # Sub-net ID

    def __str__(self) -> str:
        return self.nid if self.nid else hex(id(self))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self}>"

    def connect_to(self, target: 'Node', type: ArcType = ArcType.ENABLER, snid: Optional[str] = None) -> 'Arc':
        """Fluent API for creating arcs."""
        return Arc(self, target, type, snid=snid)


class Arc:
    """Connects a source Node to a target Node."""

    def __init__(self, source: Node, target: Node, type: ArcType = ArcType.ENABLER, snid: Optional[str] = None):
        self.source = source
        self.target = target
        self.type = type
        self.nid: Optional[str] = None
        self.snid = snid

        # Bi-directional registration
        self.source.outputs.append(self)
        self.target.inputs.append(self)

    def __str__(self) -> str:
        return self.nid if self.nid else f"Arc({self.source} -> {self.target})"

    def is_inferential(self) -> bool:
        return isinstance(self.source, Binding) or isinstance(self.target, Binding)

    def is_interleaving(self) -> bool:
        return isinstance(self.source, AnonymousPlace) or isinstance(self.target, AnonymousPlace)


# --- Petri Net Elements ---

class Place(Node):
    """A container for tokens."""

    def __init__(self, label: Optional[str] = None, marking: bool = False, snid: Optional[str] = None):
        super().__init__(snid)
        if isinstance(label, AnonymousPlace):
            raise ValueError("Label cannot be an AnonymousPlace instance.")
        self.label = label
        self.marking = marking

    def flush(self):
        self.marking = False

    def __str__(self) -> str:
        label_str = f" ({self.label})" if self.label else ""
        return f"{self.nid or hex(id(self))}{label_str}"


class AnonymousPlace(Place): pass
class ImplicitPlace(Place): pass


class Transition(Node):
    """A transformation unit that fires based on input markings."""

    def __init__(self, label: Optional[str] = None, snid: Optional[str] = None):
        super().__init__(snid)
        self.label = label

    @property
    def is_source(self) -> bool:
        return not any(isinstance(arc.source, Place) for arc in self.inputs)

    def is_enabled(self) -> bool:
        if self.is_source:
            return False

        enablers = [a for a in self.inputs if a.type == ArcType.ENABLER]
        inhibitors = [a for a in self.inputs if a.type == ArcType.INHIBITOR]

        # All enablers must have tokens, no inhibitors can have tokens
        enabled = all(isinstance(a.source, Place) and a.source.marking for a in enablers)
        inhibited = any(isinstance(a.source, Place) and a.source.marking for a in inhibitors)

        return enabled and not inhibited

    def fire(self):
        """Consumes inputs and produces outputs in one atomic-like step."""
        if not self.is_enabled():
            return

        # 1. Consume tokens
        for arc in (a for a in self.inputs if a.type == ArcType.ENABLER):
            if isinstance(arc.source, Place):
                arc.source.marking = False

        # 2. Produce / Reset tokens
        for arc in self.outputs:
            if isinstance(arc.target, Place):
                if arc.type == ArcType.ENABLER:
                    arc.target.marking = True
                elif arc.type == ArcType.RESET:
                    arc.target.flush()

    def __str__(self) -> str:
        label_str = f" ({self.label})" if self.label else ""
        return f"{self.nid or hex(id(self))}{label_str}"


class AnonymousTransition(Transition): pass


# --- Inferential Elements ---

class Binding(Node):
    """Captures logical dependencies (Horn clauses)."""

    def to_asp(self) -> str:
        """Converts binding to Answer Set Programming syntax."""
        if not self.outputs:
            return ""

        head = self.outputs[0].target.nid
        body = ", ".join(arc.source.nid for arc in self.inputs if arc.source.nid)
        return f"{head} :- {body}."


class PlaceBinding(Binding): pass
class TransitionBinding(Binding): pass


# --- Structure ---

class PetriNetStructure:
    """The container managing the lifecycle and IDs of PN elements."""

    def __init__(self, places=(), transitions=(), arcs=(), p_bindings=(), t_bindings=()):
        self.places = list(places)
        self.transitions = list(transitions)
        self.arcs = list(arcs)
        self.p_bindings = list(p_bindings)
        self.t_bindings = list(t_bindings)

        # Mapping tables
        self.registry: Dict[str, Node] = {}
        self._initialize_net()

    def _initialize_net(self):
        """Automates ID assignment and registry building."""
        categories = {
            "p": self.places,
            "t": self.transitions,
            "a": self.arcs,
            "pb": self.p_bindings,
            "tb": self.t_bindings
        }

        for prefix, collection in categories.items():
            for i, item in enumerate(collection, 1):
                nid = f"{prefix}{i}"
                item.nid = nid
                self.registry[nid] = item

    def get_marking_map(self) -> str:
        return ", ".join(f"{p.nid}: {p.marking}" for p in self.places)

    def generate_asp_code(self) -> str:
        """Generates full ASP representation."""
        p_ext = "\n".join(f"#external {p.nid}." for p in self.places)
        t_ext = "\n".join(f"#external {t.nid}." for t in self.transitions)
        pb_code = "\n".join(b.to_asp() for b in self.p_bindings)
        tb_code = "\n".join(b.to_asp() for b in self.t_bindings)

        return f"{p_ext}\n{t_ext}\n{pb_code}\n{tb_code}"

    def __str__(self) -> str:
        header = "-" * 37
        lines = [header, "Places:", *(f"{p}: '{p.label}'" for p in self.places)]
        lines += ["Transitions:", *(f"{t}: '{t.label}'" for t in self.transitions)]
        lines += ["Arcs:", *(f"{a.nid}: {a.source.nid} -> {a.target.nid}" for a in self.arcs)]
        lines.append(header)
        return "\n".join(lines)