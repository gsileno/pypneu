"""
pypneu - Visualization module using Graphviz/Pydot.
Translates Petri Net structures into graphical representations.
"""

import pydot
from typing import Dict, Any
from . import structures as pn

# Constants for styling
TOKEN_CHAR = "●"
DEFAULT_NODE_ATTRS = {"width": 0.4, "height": 0.4, "fixedsize": "true"}

class PetriNetViewer:
    """Generates Pydot graphs from PetriNetStructure objects."""

    def __init__(self, lppn: pn.PetriNetStructure):
        if not isinstance(lppn, pn.PetriNetStructure):
            raise ValueError("Input must be a PetriNetStructure")
        self.lppn = lppn

    def _get_node_style(self, element) -> Dict[str, Any]:
        """Returns the Pydot attribute dictionary for a given PN element."""
        style = DEFAULT_NODE_ATTRS.copy()

        # Check if the place is marked (boolean in your structures.py)
        is_filled = getattr(element, 'marking', False)

        # Labeling Logic:
        # For places, we put the Token inside the circle.
        # For transitions, we keep them empty but label them with their name.
        style['label'] = TOKEN_CHAR if is_filled else ""

        if hasattr(element, 'label') and element.label:
            # xlabel places the text outside the node so it doesn't overlap the token
            style['xlabel'] = str(element.label)

        # Type-specific shape overrides
        if isinstance(element, pn.Place):
            style.update({"shape": "circle"})
        elif isinstance(element, pn.Transition):
            style.update({"shape": "box", "style": "filled", "fillcolor": "white"})
            # If it's a source transition, maybe give it a slight tint
            if element.is_source:
                style.update({"fillcolor": "#e8f5e9"}) # Very light green

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

        # 1. Process Nodes (Places and Transitions)
        for p in self.lppn.places:
            attrs = self._get_node_style(p)
            node = pydot.Node(p.nid, **attrs)
            id_to_pydot_node[p.nid] = node
            graph.add_node(node)

        for t in self.lppn.transitions:
            attrs = self._get_node_style(t)
            node = pydot.Node(t.nid, **attrs)
            id_to_pydot_node[t.nid] = node
            graph.add_node(node)

        # 2. Process Arcs using ArcType for styling
        for arc in self.lppn.arcs:
            edge_attrs = {"style": "solid"}

            # Map ArcTypes to Graphviz arrowheads
            if arc.type == pn.ArcType.INHIBITOR:
                edge_attrs["arrowhead"] = "dot" # Standard circle for inhibition
            elif arc.type == pn.ArcType.RESET:
                edge_attrs["arrowhead"] = "diamond"
                edge_attrs["style"] = "dashed"
            elif arc.type == pn.ArcType.ENABLER:
                edge_attrs["arrowhead"] = "normal"

            pydot_edge = pydot.Edge(
                id_to_pydot_node[arc.source.nid],
                id_to_pydot_node[arc.target.nid],
                **edge_attrs
            )
            graph.add_edge(pydot_edge)

        return graph

    def save_png(self, filename: str):
        """Helper to render the graph directly to a file."""
        self.to_pydot_graph().write_png(filename)