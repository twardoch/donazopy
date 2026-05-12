# this_file: src/donazopy/__main__.py
"""Command-line entry point for donazopy."""

import fire

from donazopy.cli import Donazopy


def main() -> None:
    """Run the Fire-powered donazopy CLI."""
    fire.Fire(Donazopy)


if __name__ == "__main__":
    main()
