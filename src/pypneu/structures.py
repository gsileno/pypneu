import logging
from enum import IntEnum, auto
from typing import List, Optional, Dict, Union

# Set up logging for internal structure debugging
logger = logging.getLogger("pypneu.structures")


class ArcType(IntEnum):
    ENABLER = auto()  # Standard flow (consumes)
    INHIBITOR = auto()  # Blocks if source has token (does not consume)
    RESET = auto()  # Flushes target marking


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
        # Bi-directional link
        self.source.outputs.append(self)
        self.target.inputs.append(self)

    def __repr__(self) -> str:
        src_label = getattr(self.source, 'label', self.source.nid)
        tgt_label = getattr(self.target, 'label', self.target.nid)
        return f"<Arc {self.nid}: {src_label} --({self.type.name})--> {tgt_label}>"


class Place(Node):
    def __init__(self, label: Optional[str] = None, marking: bool = False):
        super().__init__()
        self.label = label
        self.marking = marking

    def flush(self):
        logger.debug(f"Flushing place {self.label} ({self.nid})")
        self.marking = False

    def __str__(self) -> str:
        return f"{self.nid} ({self.label})" if self.label else f"{self.nid}"


class Transition(Node):
    def __init__(self, label: Optional[str] = None):
        super().__init__()
        self.label = label
        self.fired_count = 0  # Track executions to enforce "max once" for sources

    @property
    def is_source(self) -> bool:
        """A transition is a source if it has no incoming ENABLER arcs from Places."""
        enablers = [a for a in self.inputs if isinstance(a.source, Place) and a.type == ArcType.ENABLER]
        return len(enablers) == 0

    def is_enabled(self) -> bool:
        """Checks if all enablers are present and no inhibitors are blocking."""
        enablers = [a for a in self.inputs if a.type == ArcType.ENABLER]
        inhibitors = [a for a in self.inputs if a.type == ArcType.INHIBITOR]

        enabled = all(isinstance(a.source, Place) and a.source.marking for a in enablers)
        inhibited = any(isinstance(a.source, Place) and a.source.marking for a in inhibitors)

        return enabled and not inhibited

    def consume_input_tokens(self):
        """Removes tokens from all connected ENABLER input places and increments fired_count."""
        for a in (x for x in self.inputs if x.type == ArcType.ENABLER):
            if isinstance(a.source, Place) and a.source.marking:
                logger.debug(f"Consuming token from {a.source.label}")
                a.source.marking = False

        # Increment firing count (important for source transitions)
        self.fired_count += 1

    def produce_output_tokens(self):
        """Produces tokens in target places or flushes them on RESET arcs."""
        for a in self.outputs:
            if isinstance(a.target, Place):
                if a.type == ArcType.ENABLER:
                    logger.debug(f"Producing token into {a.target.label}")
                    a.target.marking = True
                elif a.type == ArcType.RESET:
                    a.target.flush()

    def __str__(self) -> str:
        return f"{self.nid} ({self.label})" if self.label else f"{self.nid}"


class PetriNetStructure:
    def __init__(self, places=(), transitions=(), arcs=()):
        self.places: List[Place] = list(places)
        self.transitions: List[Transition] = list(transitions)
        self.arcs: List[Arc] = list(arcs)
        self.registry: Dict[str, Union[Place, Transition, Arc]] = {}
        self._initialize_net()

    def _initialize_net(self):
        cat = {"p": self.places, "t": self.transitions, "a": self.arcs}
        for prefix, collection in cat.items():
            for i, item in enumerate(collection, 1):
                nid = f"{prefix}{i}"
                item.nid = nid
                self.registry[nid] = item

    @property
    def id2place(self) -> Dict[str, Place]:
        return {p.nid: p for p in self.places}

    def marking_to_string(self) -> str:
        return ", ".join(f"{p.label}: {'●' if p.marking else '○'}" for p in self.places)