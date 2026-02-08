from enum import IntEnum, auto
from typing import List, Optional, Dict


class ArcType(IntEnum):
    ENABLER = auto()  # Standard flow (consumes)
    INHIBITOR = auto()  # Blocks if source has token (does not consume)
    RESET = auto()  # Flushes target


class Node:
    def __init__(self, snid: Optional[str] = None):
        self.inputs: List['Arc'] = []
        self.outputs: List['Arc'] = []
        self.nid: Optional[str] = None
        self.snid: Optional[str] = snid

    def __str__(self) -> str:
        return self.nid if self.nid else hex(id(self))


class Arc:
    def __init__(self, source: Node, target: Node, type: ArcType = ArcType.ENABLER):
        self.source = source
        self.target = target
        self.type = type
        self.nid: Optional[str] = None
        self.source.outputs.append(self)
        self.target.inputs.append(self)

    def __repr__(self) -> str:
        # Crucial for debugging arc counts: shows who is connected to whom
        src_label = getattr(self.source, 'label', self.source.nid)
        tgt_label = getattr(self.target, 'label', self.target.nid)
        return f"<Arc {self.nid}: {src_label} --({self.type.name})--> {tgt_label}>"


class Place(Node):
    def __init__(self, label: Optional[str] = None, marking: bool = False):
        super().__init__()
        self.label = label
        self.marking = marking

    def flush(self):
        self.marking = False

    def __str__(self) -> str:
        return f"{self.nid} ({self.label})" if self.label else f"{self.nid}"


class Transition(Node):
    def __init__(self, label: Optional[str] = None):
        super().__init__()
        self.label = label

    @property
    def is_source(self) -> bool:
        # Filter for arcs coming from Places that are specifically ENABLERS
        enabler_inputs = [a for a in self.inputs if isinstance(a.source, Place) and a.type == ArcType.ENABLER]

        # DEBUG TRACE: This will print during your unit test failure
        if len(enabler_inputs) > 0:
            print(f"\n[DEBUG] Transition '{self.label}' is NOT a source.")
            print(f"  Reason: Found {len(enabler_inputs)} enabler input(s):")
            for a in enabler_inputs:
                print(f"    - Source: '{a.source.label}' (NID: {a.source.nid})")

        return len(enabler_inputs) == 0

    def is_enabled(self) -> bool:
        enablers = [a for a in self.inputs if a.type == ArcType.ENABLER]
        inhibitors = [a for a in self.inputs if a.type == ArcType.INHIBITOR]

        enabled = all(isinstance(a.source, Place) and a.source.marking for a in enablers)
        inhibited = any(isinstance(a.source, Place) and a.source.marking for a in inhibitors)
        return enabled and not inhibited

    def fire(self):
        if not self.is_enabled(): return
        for a in (x for x in self.inputs if x.type == ArcType.ENABLER):
            if isinstance(a.source, Place): a.source.marking = False
        for a in self.outputs:
            if isinstance(a.target, Place):
                if a.type == ArcType.ENABLER:
                    a.target.marking = True
                elif a.type == ArcType.RESET:
                    a.target.flush()

    def __str__(self) -> str:
        return f"{self.nid} ({self.label})" if self.label else f"{self.nid}"


class PetriNetStructure:
    def __init__(self, places=(), transitions=(), arcs=()):
        self.places = list(places)
        self.transitions = list(transitions)
        self.arcs = list(arcs)
        self.registry = {}
        self._initialize_net()

    def _initialize_net(self):
        cat = {"p": self.places, "t": self.transitions, "a": self.arcs}
        for prefix, collection in cat.items():
            for i, item in enumerate(collection, 1):
                nid = f"{prefix}{i}"
                item.nid = nid
                self.registry[nid] = item

    def __str__(self) -> str:
        h = "-" * 37
        lines = [h, "Places:"] + [f"{p}" for p in self.places]
        lines += ["Transitions:"] + [f"{t}" for t in self.transitions]
        lines += ["Arcs:"]
        for a in self.arcs:
            t_str = f" ({a.type.name})" if a.type != ArcType.ENABLER else ""
            lines.append(f"{a.nid}: {a.source.nid} -> {a.target.nid}{t_str}")
        return "\n".join(lines + [h])