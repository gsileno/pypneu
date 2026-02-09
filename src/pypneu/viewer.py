"""
pypneu - Visualization module using Graphviz/Pydot.
Translates Petri Net structures into graphical representations.
"""

import pydot
from typing import Dict, Any, List, Optional
from pypneu.structures import PetriNetStructure, Place, Transition, Arc, ArcType

# Constants for styling
TOKEN_CHAR = "●"
DEFAULT_NODE_ATTRS = {"width": 0.4, "height": 0.4, "fixedsize": "true"}

class PetriNetViewer:
    """Generates Pydot graphs from PetriNetStructure objects."""

    def __init__(
        self,
        net: PetriNetStructure,
        highlight_green: List[str] = None,
        highlight_red: List[str] = None
    ):
        if not isinstance(net, PetriNetStructure):
            raise ValueError("Input must be a PetriNetStructure")
        self.pn = net
        # NIDs or Labels to highlight green (Enabled/Fired)
        self.highlight_green = highlight_green or []
        # NIDs or Labels to highlight red (Blocked/Inhibited)
        self.highlight_red = highlight_red or []

    def _get_node_style(self, element) -> Dict[str, Any]:
        """Returns the Pydot attribute dictionary for a given PN element."""
        style = DEFAULT_NODE_ATTRS.copy()

        # Check marking state
        is_filled = getattr(element, 'marking', False)
        style['label'] = TOKEN_CHAR if is_filled else ""

        if hasattr(element, 'label') and element.label:
            style['xlabel'] = str(element.label)

        # Type-specific shape overrides
        if isinstance(element, Place):
            style.update({"shape": "circle"})

        elif isinstance(element, Transition):
            style.update({"shape": "box", "style": "filled", "fillcolor": "white"})

            # Identify ID and Label for lookup
            nid, label = element.nid, element.label

            # --- HIGHLIGHT LOGIC ---
            if nid in self.highlight_green or label in self.highlight_green:
                # ENABLED / FIRED
                style.update({
                    "fillcolor": "#90ee90",  # Light Green
                    "color": "#006400",      # Dark Green border
                    "penwidth": "2.5"
                })
            elif nid in self.highlight_red or label in self.highlight_red:
                # BLOCKED BY INHIBITOR
                style.update({
                    "fillcolor": "#ffcccb",  # Light Red
                    "color": "#8b0000",      # Dark Red border
                    "penwidth": "2.5",
                    "style": "filled,dashed"  # Dashed border for "blocked"
                })
            elif element.is_source:
                style.update({"fillcolor": "#f0f8ff"})

        return style

    def to_pydot_graph(self) -> pydot.Dot:
        """Constructs a pydot.Dot object representing the net."""
        graph = pydot.Dot(
            graph_type='digraph',
            rankdir="LR",
            nodesep=0.5,
            ranksep=0.7,
            margin=0.5,
            forcelabels="true"
        )

        id_to_pydot_node = {}

        # 1. Process Nodes
        for p in self.pn.places:
            node = pydot.Node(p.nid, **self._get_node_style(p))
            id_to_pydot_node[p.nid] = node
            graph.add_node(node)

        for t in self.pn.transitions:
            node = pydot.Node(t.nid, **self._get_node_style(t))
            id_to_pydot_node[t.nid] = node
            graph.add_node(node)

        # 2. Process Arcs
        for arc in self.pn.arcs:
            edge_attrs = {"style": "solid"}

            if arc.type == ArcType.INHIBITOR:
                edge_attrs["arrowhead"] = "dot"
            elif arc.type == ArcType.RESET:
                edge_attrs["arrowhead"] = "diamond"
                edge_attrs["style"] = "dashed"

            graph.add_edge(pydot.Edge(
                id_to_pydot_node[arc.source.nid],
                id_to_pydot_node[arc.target.nid],
                **edge_attrs
            ))

        return graph

    def save_png(self, filename: str):
        """Helper to render the graph directly to a file."""
        self.to_pydot_graph().write_png(filename)