import logging
import tempfile
from pathlib import Path

import pytest
from rdflib import Graph

from . import extract_mermaid, mermaid_to_rdf, parse_line2, parse_mermaid

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


@pytest.mark.parametrize(
    "line, expected",
    [
        ("A --> B --> C", [("A", "-->", None), ("B", "-->", None), ("C", None, None)]),
        (
            "A --o |comment| B --o C",
            [("A", "--o", "comment"), ("B", "--o", None), ("C", None, None)],
        ),
        (
            "A--o|comment|B--oC",
            [("A", "--o", "comment"), ("B", "--o", None), ("C", None, None)],
        ),
        ("A", [("A", None, None)]),
        (
            "A[label] --o |comment| B[[label]]",
            [
                ("A[label]", "--o", "comment"),
                ("B[[label]]", None, None),
            ],
        ),
        (
            "A -.-x B ---o C ---> D",
            [
                ("A", "-.-x", None),
                ("B", "---o", None),
                ("C", "--->", None),
                ("D", None, None),
            ],
        ),
    ],
)
def test_parse_line2(line, expected):
    ret = parse_line2(line)
    assert ret == expected


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


def test_g1():
    text = Path("README.md").read_text()
    graphs = extract_mermaid(text)
    for graph in graphs:
        turtle = parse_mermaid(graph)
        # Create a temporary file.
        tmp_ttl = tempfile.NamedTemporaryFile(suffix=".ttl", delete=False).name
        Path(tmp_ttl).write_text(turtle)
        g = Graph()
        g.parse(tmp_ttl, format="turtle")
