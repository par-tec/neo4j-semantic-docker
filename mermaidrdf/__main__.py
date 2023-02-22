from pathlib import Path

import click
from rdflib import Graph

from . import extract_mermaid, parse_mermaid
from .to_mermaid import MermaidRDF


@click.command()
@click.argument("basepath", type=click.Path(exists=True))
@click.argument(
    "destfile",
    type=click.Path(exists=False),
    default="deleteme.ttl",
)
@click.option(
    "--reverse",
    default=False,
    is_flag=True,
    help="Convert from RDF to Mermaid",
)
def main(basepath, destfile, reverse):
    breakpoint()
    if reverse:
        rdf_to_mermaid(basepath, destfile)
    else:
        mermaid_to_rdf(basepath, destfile)


def rdf_to_mermaid(basepath, destfile="deleteme.mmd"):
    files = (
        (Path(basepath),)
        if basepath.endswith(".ttl")
        else Path(basepath).glob("**/*.ttl")
    )
    breakpoint()
    for f in files:
        g = Graph()
        g.parse(f, format="turtle")
        mermaid = MermaidRDF(g)
        mermaid_text = mermaid.render()
        Path(destfile).write_text(mermaid_text)


def mermaid_to_rdf(basepath, destfile):
    turtle = ""
    files = (
        (Path(basepath),)
        if basepath.endswith(".md")
        else Path(basepath).glob("**/*.md")
    )
    for f in files:
        mermaid_graphs = extract_mermaid(f.read_text())
        for graph in mermaid_graphs:
            turtle += "\n" + parse_mermaid(graph)
    Path(destfile).write_text(turtle)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
