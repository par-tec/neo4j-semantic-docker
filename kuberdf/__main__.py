from pathlib import Path

import click
from rdflib import Graph

from mermaidrdf import MermaidRDF

from . import parse_manifests
from .neo4j import run_queries


@click.command()
@click.argument("basepath", type=click.Path(exists=True))
@click.argument(
    "destfile",
    type=click.Path(exists=False),
    default="deleteme",
)
@click.argument(
    "neo4j",
    default="neo4j://localhost:7687",
    required=False,
)
@click.option(
    "--ns-from-file",
    default=True,
    is_flag=True,
    help="Use the filename as the namespace",
)
@click.option(
    "--mermaid",
    default=False,
    is_flag=True,
    help="Convert from RDF to Mermaid",
)
def main(basepath, destfile, neo4j, ns_from_file, mermaid):
    parse_manifests(
        Path(basepath).glob("**/*.y*ml"), outfile=destfile, ns_from_file=True
    )

    if mermaid:
        g = Graph()
        g.parse(Path(destfile).with_suffix(".ttl"), format="turtle")
        mermaid = MermaidRDF(g)
        mermaid_text = mermaid.render()
        Path(destfile).with_suffix(".md").write_text(
            f"""# Sample

```mermaid
{mermaid_text}
```
"""
        )
    neo4j_init = Path("neo4j.init")
    if not neo4j_init.exists():
        return
    queries = Path("neo4j.init").read_text().split(";")
    run_queries(neo4j, queries)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
