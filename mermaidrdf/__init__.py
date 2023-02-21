import logging
import re
from collections import defaultdict
from pathlib import Path

import yaml
from rdflib import Graph, Namespace

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

MERMAID_KEYWORDS = (
    "subgraph",
    "end",
    "classDef",
    "class",
)
PAT_LABEL = r"(.*?)"
PAT_OPEN = r"|".join((r"\[\[", r"\[\(", r"\(\(", r"\{\{", r"\[\/"))
PAT_CLOSE = r"|".join((r"\]\]", r"\)\]", r"\)\)", r"\}\}", r"\/\]"))
PAT_NODE = r"(\w+)" r"(([\(\[\{\/]{1,2})" + PAT_LABEL + r"([\)\]\}\/]{1,2}))?"
PAT_ARROW = r"\s*(-->|--o|-[.-]+-[>ox]?)" + r"\s*" + r"(?:\|(.*)?\|)?\s*"
PAT_LINE = rf"{PAT_NODE}({PAT_ARROW}{PAT_NODE})*"
RE_ARROW = re.compile(PAT_ARROW)
RE_LINE = re.compile(PAT_LINE)
RE_NODE = re.compile(PAT_NODE)

NS_DEFAULT = Namespace("https://par-tec.it/example#")
NS_D3F = Namespace("http://d3fend.mitre.org/ontologies/d3fend.owl#")
DATAFILE = Path(__file__).parent / "mermaidrdf.yaml"
DATA = yaml.safe_load(DATAFILE.read_text())
SW_MAP = {tuple(x["labels"]): x["artifacts"] for x in DATA["SW_MAP"]}
FONTAWESOME_MAP = {tuple(x["labels"]): x["artifacts"] for x in DATA["FONTAWESOME_MAP"]}
D3F_PROPERTIES = set(DATA["D3F_PROPERTIES"])
D3F_INFERRED_RELATIONS = defaultdict(
    list, **{x["relation"]: x["predicates"] for x in DATA["INFERRED_RELATIONS"]}
)


def mermaid_to_rdf(mermaid):
    mermaid = mermaid.strip()
    # Ensure that the mermaid text starts with "graph "
    if not mermaid.startswith(("graph ", "graph")):
        raise ValueError("The mermaid text must start with 'graph'")
    # Split the mermaid text into lines, skipping the first line.
    lines = mermaid.splitlines()[1:]

    for line in lines:
        for sentence in parse_line(line):
            yield sentence


def parse_mermaid(mermaid: str):
    g = Graph()
    g.bind("", NS_DEFAULT)
    g.bind("d3f", NS_D3F)
    g.bind("rdfs", "http://www.w3.org/2000/01/rdf-schema#")
    turtle = """@prefix : <https://par-tec.it/example#> .
    @prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
    @prefix d3f: <http://d3fend.mitre.org/ontologies/d3fend.owl#> .
    """ + "\n".join(
        mermaid_to_rdf(mermaid)
    )
    g.parse(data=turtle, format="turtle")
    return g.serialize(format="turtle")


def render_node(id_, label, sep):
    type_ = ":Node"
    rdf = [f":{id_} a {type_} ."]

    if sep == "[(":
        type_ = "d3f:DatabaseServer"
    elif sep == "[[":  # FIXME: is this ok?
        type_ = "d3f:Server"
    rdf.append(f":{id_} a {type_} .")
    if label:
        rdf += [f':{id_} rdfs:label """{label}""" .']

    label = label or id_
    for softwares, d3f_classes in SW_MAP.items():
        if any((x in label.lower() for x in softwares)):
            log.info("Found property %s in label %s", softwares, label)
            rdf += [f":{id_} a {','.join(d3f_classes)} ."]
    for needles, d3f_classes in FONTAWESOME_MAP.items():
        if any((x in label.lower() for x in needles)):
            log.info("Found relation %s in label %s", needles, label)
            rdf += [f":{id_} d3f:related {','.join(d3f_classes)} ."]
    for needle in re.findall("(d3f:[a-zA-Z-0-9]+)", label):
        log.info("Found class %s in label %s", needle, label)
        rdf += [f":{id_} a {needle} ."]
    return id_, rdf


def parse_line2(line):
    """Parse a mermaid line in the possible forms:
    1. x[label]
    2. x[label]-->y
    3. x[label]-->|comment| y
    4. x --> y --> z
    """
    ret = RE_ARROW.split(line)
    # Pad the list with None to make sure we have a multiple of 3 length.
    ret = ret + [None] * (3 - len(ret) % 3)
    return [tuple(ret[i : i + 3]) for i in range(0, len(ret), 3)]


def parse_line(line):
    """Parse a mermaid line consisting of two nodes and an arrow.
    If the line is not valid, skip it."""
    # Skip empty lines
    line = line.strip()
    if not line or len(line) < 5 or line.startswith("%%"):
        return

    if line.startswith(MERMAID_KEYWORDS):
        log.warning(f"Unsupported KEYWORD: {line}")
        return
    # if the line doesn't match x-->y, skip it
    if not RE_LINE.match(line):
        log.warning(f"Unsupported RE_LINE: {line}")
        return
    # Split the line into the two nodes and the arrow
    # according to the mermaid syntax. The resulting line will be
    # something like 5-1-5
    parsed_line = parse_line2(line)
    log.info(f"Parsed line: {line} to: {parsed_line}")

    node_id0, arrow0, relation0 = None, None, None
    for node, arrow, relation in parsed_line:
        id_, _, sep, label, _ = RE_NODE.match(node).groups()
        # Remove the trailing and leading quotes from the nodes
        node_id, node1_rdf = render_node(id_=id_, label=label, sep=sep)
        yield from node1_rdf
        if node_id0:
            # TODO handle the relation.

            if not (node and arrow0):
                raise NotImplementedError
            # Create the RDF
            if arrow0.endswith("->"):
                predicate = "d3f:accesses"
            elif arrow0.endswith("-o"):
                predicate = "d3f:reads"
            elif arrow0.endswith("-"):
                predicate = ":connected"
            else:
                raise NotImplementedError(f"Unsupporte predicate: {arrow}")

            yield from _parse_relation(node_id0, node_id, predicate, relation0)

        node_id0, arrow0, relation0 = node_id, arrow, relation


def _parse_relation(src, dst, predicate, relation):
    """Parse a relation between two nodes."""
    if not relation:
        yield f":{src} {predicate} :{dst} ."
        return
    if relation.startswith("d3f:") and relation[4:] in D3F_PROPERTIES:
        yield f":{src} {relation} :{dst} ."

        for predicate in D3F_INFERRED_RELATIONS[relation]:
            yield predicate.format(subject=src, object=dst)
        return

    # Explicit the relationship.
    yield f":{src} {predicate} :{dst} ."

    # Introduces a relation based on a specific d3f:DigitalArtifact,
    # e.g. :App --> |via d3f:DatabaseQuery| :Database
    for needle in re.findall(r"(d3f:[A-Za-z0-9._\.-]+)", relation):
        # TODO verify that the relation is a valid d3f:DigitalArtifact.
        yield f":{src} d3f:produces {needle} ."
        yield f":{dst} d3f:uses {needle} ."
        return

    # Introduces a relation based on a specific d3f:DigitalArtifact,
    # e.g. :Client --> |via fa:fa-envelope| :MTA
    for rel in re.findall(r"(?:fab?:(fa-[a-z0-9-]+))", relation):
        for needles, d3f_classes in FONTAWESOME_MAP.items():
            if rel not in needles:
                continue
            for d3f_class in d3f_classes:
                yield f":{src} d3f:produces {d3f_class} ."
                yield f":{dst} d3f:uses {d3f_class} ."
        return


def extract_mermaid(text: str):
    re_mermaid = re.compile("```mermaid\n.*?\n```", re.DOTALL | re.MULTILINE)
    return [graph[10:-3].strip() for graph in re_mermaid.findall(text)]
