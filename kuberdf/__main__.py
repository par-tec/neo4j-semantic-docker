from pathlib import Path

import click

from . import parse_manifests


@click.command()
@click.argument("basepath", type=click.Path(exists=True))
@click.argument(
    "destfile",
    type=click.Path(exists=False),
    default="deleteme",
)
def main(basepath, destfile):
    parse_manifests(Path(basepath).glob("**/*.yaml"), destfile)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
