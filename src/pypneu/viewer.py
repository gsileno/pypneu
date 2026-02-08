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

        # Base Labeling Logic
        is_filled = getattr(element, 'marking', False)
        style['label'] = TOKEN_CHAR if is_filled else ""
        if hasattr(element, 'label') and element.label:
            style['xlabel'] = str(element.label)

        # Type-specific overrides
        if isinstance(element, pn.AnonymousPlace):
            style.update({"shape": "circle", "color": "gray"})
        elif isinstance(element, pn.ImplicitPlace):
            style.update({"shape": "circle", "style": "dashed"})
        elif isinstance(element, pn.Place):
            style.update({"shape": "circle", "labelloc": "top"})
        elif isinstance(element, pn.AnonymousTransition):
            style.update({"shape": "box", "color": "gray", "label": ""})
        elif isinstance(element, pn.Transition):
            style.update({"shape": "box", "label": ""})
        elif isinstance(element, pn.PlaceBinding):
            style.update({"shape": "box", "style": "filled", "fillcolor": "black",
                          "width": 0.2, "height": 0.2, "label": ""})
        elif isinstance(element, pn.TransitionBinding):
            style.update({"shape": "circle", "style": "filled", "fillcolor": "black",
                          "width": 0.2, "height": 0.2, "label": ""})

        return style

    def to_pydot_graph(self) -> pydot.Dot:
        """Constructs a pydot.Dot object representing the net."""
        graph = pydot.Dot(
            graph_type='digraph',
            rankdir="LR",
            nodesep=0.5,
            margin=0.5,
            forcelabels="true"
        )

        id_to_pydot_node = {}
        subgraphs: Dict[str, pydot.Subgraph] = {}

        # 1. Process all Nodes (Places, Transitions, Bindings)
        all_elements = (list(self.lppn.places) + list(self.lppn.transitions) +
                        list(self.lppn.p_bindings) + list(self.lppn.t_bindings))

        for elem in all_elements:
            attrs = self._get_node_style(elem)
            node = pydot.Node(elem.nid, **attrs)
            id_to_pydot_node[elem.nid] = node

            # Handle Clustering (Sub-nets)
            if elem.snid:
                if elem.snid not in subgraphs:
                    subgraphs[elem.snid] = pydot.Subgraph(
                        f"cluster_{elem.snid}",
                        color="lightgrey",
                        label=f"Subnet {elem.snid}"
                    )
                    graph.add_subgraph(subgraphs[elem.snid])
                subgraphs[elem.snid].add_node(node)
            else:
                graph.add_node(node)

        # 2. Process Arcs
        for arc in self.lppn.arcs:
            edge_style = "dotted" if arc.is_inferential() else "solid"
            pydot_edge = pydot.Edge(
                id_to_pydot_node[arc.source.nid],
                id_to_pydot_node[arc.target.nid],
                style=edge_style
            )

            # If both ends are in the same cluster, add edge to that subgraph
            if arc.source.snid and arc.source.snid == arc.target.snid:
                subgraphs[arc.source.snid].add_edge(pydot_edge)
            else:
                graph.add_edge(pydot_edge)

        return graph

    def save_png(self, filename: str):
        """Helper to render the graph directly to a file."""
        self.to_pydot_graph().write_png(filename)