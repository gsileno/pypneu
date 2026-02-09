import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from .structures import PetriNetStructure, ArcType, Place, Transition


def to_json(pn: PetriNetStructure) -> str:
    """Exports the Petri net to a custom JSON format."""
    data = {
        "places": [{"id": p.nid, "label": p.label, "marking": int(p.marking)} for p in pn.places],
        "transitions": [{"id": t.nid, "label": t.label} for t in pn.transitions],
        "arcs": [
            {
                "id": a.nid,
                "source": a.source.nid,
                "target": a.target.nid,
                "type": a.type.name
            } for a in pn.arcs
        ]
    }
    return json.dumps(data, indent=4)


def to_pnml(pn: PetriNetStructure, filename: str):
    """Exports the Petri net to standard PNML (Petri Net Markup Language)."""
    pnml = ET.Element("pnml")
    net = ET.SubElement(pnml, "net", id="net1", type="http://www.pnml.org/version-2009/grammar/pnmlcoremodel")
    page = ET.SubElement(net, "page", id="page1")

    for p in pn.places:
        place = ET.SubElement(page, "place", id=p.nid)
        name = ET.SubElement(place, "name")
        ET.SubElement(name, "text").text = p.label or p.nid
        initial_marking = ET.SubElement(place, "initialMarking")
        ET.SubElement(initial_marking, "text").text = str(int(p.marking))

    for t in pn.transitions:
        trans = ET.SubElement(page, "transition", id=t.nid)
        name = ET.SubElement(trans, "name")
        ET.SubElement(name, "text").text = t.label or t.nid

    for a in pn.arcs:
        # PNML standards usually handle flow; custom types like INHIBITOR
        # are often extension-dependent, but we export them as 'arc' here.
        arc = ET.SubElement(page, "arc", id=a.nid, source=a.source.nid, target=a.target.nid)
        if a.type != ArcType.ENABLER:
            type_val = ET.SubElement(arc, "type")
            ET.SubElement(type_val, "text").text = a.type.name.lower()

    # Pretty print XML
    xml_str = ET.tostring(pnml, encoding='utf-8')
    pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")

    with open(filename, "w", encoding='utf-8') as f:
        f.write(pretty_xml)


def to_dot(pn: PetriNetStructure) -> str:
    """Generates a Graphviz DOT string for visualization."""
    lines = ["digraph G {", "    rankdir=LR;"]

    # Places: Circles
    for p in pn.places:
        label = f"{p.label}\\n({1 if p.marking else 0})"
        lines.append(f'    "{p.nid}" [label="{label}", shape=circle];')

    # Transitions: Rectangles
    for t in pn.transitions:
        label = t.label or t.nid
        lines.append(f'    "{t.nid}" [label="{label}", shape=box, style=filled, fillcolor=lightgrey];')

    # Arcs
    for a in pn.arcs:
        attrs = []
        if a.type == ArcType.INHIBITOR:
            attrs.append("arrowhead=dot")
        elif a.type == ArcType.RESET:
            attrs.append("arrowhead=vee")
            attrs.append("style=dashed")
        elif a.type == ArcType.ENABLER:
            attrs.append("arrowhead=normal")

        attr_str = f" [{', '.join(attrs)}]" if attrs else ""
        lines.append(f'    "{a.source.nid}" -> "{a.target.nid}"{attr_str};')

    lines.append("}")
    return "\n".join(lines)