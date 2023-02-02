import logging
from pathlib import Path

from rdflib import Graph

from . import extract_mermaid, mermaid_to_rdf, mermaid_to_ttl

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


def test_mermaid_to_rdf():
    # Given
    mermaid = """
graph TD
    A --> B
    A[(mysql)] --> D
    B-->C
    A--oC
    """
    # When
    rdf = set(mermaid_to_rdf(mermaid))
    # Then
    assert rdf == {
        ":A d3f:accesses :B .",
        ":A d3f:accesses :D .",
        ":A d3f:reads :C .",
        ":A a :Node .",
        ":A a d3f:DatabaseServer .",
        ':A rdfs:label """mysql""" .',
        ":B d3f:accesses :C .",
        ":B a :Node .",
        ":C a :Node .",
        ":D a :Node .",
    }


def test_extract_bash_blocks_from_markdown():
    """Extract bash blocks form a markdown text"""
    text = Path("README.md").read_text()
    ret = extract_mermaid(text)
    for block in ret:
        assert block.startswith("graph")


def test_m2d3f():
    text = Path("README.md").read_text()

    graphs = extract_mermaid(text)
    for graph in graphs:
        ret = mermaid_to_rdf(graph)
        ret = set(ret)
        raise NotImplementedError


def test_g1():
    text = Path("README.md").read_text()
    graphs = extract_mermaid(text)
    turtle = mermaid_to_ttl(graphs[0])
    Path("infra.ttl").write_text(turtle)
    g = Graph()
    g.parse("infra.ttl", format="turtle")
