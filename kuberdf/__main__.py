from pathlib import Path

import click

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
def main(basepath, destfile, neo4j):
    parse_manifests(Path(basepath).glob("**/*.yaml"), destfile)

    queries = Path("neo4j.init").read_text().split(";")
    run_queries(neo4j, queries)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
