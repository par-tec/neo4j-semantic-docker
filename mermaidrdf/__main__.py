from pathlib import Path

import click

from . import extract_mermaid, parse_mermaid


@click.command()
@click.argument("basepath", type=click.Path(exists=True))
@click.argument(
    "destfile",
    type=click.Path(exists=False),
    default="deleteme.ttl",
)
def main(basepath, destfile):
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
