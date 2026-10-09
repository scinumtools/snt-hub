from __future__ import annotations

import argparse
from pathlib import Path

from .generator import ROOT, generate
from .hub import SetupError, recipes, setup


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Quantum ESPRESSO pw.x input from DIPL.")
    sub = parser.add_subparsers(dest="command", required=True)
    generated = sub.add_parser("generate")
    generated.add_argument("--setup", default="si_scf")
    generated.add_argument("--output", type=Path, required=True)
    generated.add_argument("--bundle", type=Path, default=ROOT)
    generated.add_argument("--override-file", type=Path)
    prepared = sub.add_parser("setup")
    prepared.add_argument("--setup", required=True)
    prepared.add_argument("--output", type=Path, required=True)
    prepared.add_argument("--bundle", type=Path, default=ROOT)
    prepared.add_argument("--source", type=Path)
    prepared.add_argument("--inputs-only", action="store_true")
    prepared.add_argument("--override-file", type=Path)
    listed = sub.add_parser("examples")
    listed.add_argument("--bundle", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        if args.command == "generate":
            print(generate(args.output, args.setup, args.bundle, args.override_file))
        elif args.command == "setup":
            print(setup(args.setup, args.output, bundle_root=args.bundle,
                        source_root=args.source, inputs_only=args.inputs_only,
                        override_file=args.override_file))
        else:
            for name, recipe in recipes(args.bundle).items():
                print(f"{name}\t{recipe['capability']}")
    except (SetupError, RuntimeError, OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
