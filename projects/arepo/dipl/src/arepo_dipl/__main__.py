from __future__ import annotations

import argparse
from pathlib import Path

from .generator import SETUPS, generate


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Arepo configuration from semantic DIPL.")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("generate")
    command.add_argument("--output", type=Path, default=Path("generated"))
    command.add_argument(
        "--setup",
        choices=tuple(SETUPS),
        default="cosmological_star_formation",
    )
    args = parser.parse_args()
    if args.command == "generate":
        print(generate(args.output, args.setup))


if __name__ == "__main__":
    main()
