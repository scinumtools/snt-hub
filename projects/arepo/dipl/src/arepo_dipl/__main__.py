from __future__ import annotations

import argparse
from pathlib import Path

from .generator import ROOT, generate
from .hub import SetupError, recipes, setup
from .workflow import build, run


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Arepo configuration from semantic DIPL.")
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("generate")
    command.add_argument("--output", type=Path, default=Path("generated"))
    command.add_argument("--setup", default="cosmological_star_formation")
    command.add_argument("--bundle", type=Path, default=ROOT)
    command.add_argument("--override-file", type=Path)
    prepared = sub.add_parser("setup", help="Prepare a complete example or native inputs only")
    prepared.add_argument("--setup", required=True)
    prepared.add_argument("--output", type=Path, required=True)
    prepared.add_argument("--bundle", type=Path, default=ROOT)
    prepared.add_argument("--source", type=Path)
    prepared.add_argument("--inputs-only", action="store_true")
    prepared.add_argument("--override-file", type=Path)
    listed = sub.add_parser("examples", help="List setup capabilities")
    listed.add_argument("--bundle", type=Path, default=ROOT)
    building = sub.add_parser("build", help="Build Arepo for a prepared setup")
    building.add_argument("--bundle", type=Path, required=True)
    building.add_argument("--source", type=Path, required=True)
    building.add_argument("--workspace", type=Path, required=True)
    building.add_argument("--setup-dir", type=Path, required=True)
    building.add_argument("--output", type=Path, required=True)
    building.add_argument("--profile", default="local")
    running = sub.add_parser("run", help="Run a complete setup as an MPI singleton")
    running.add_argument("--bundle", type=Path, required=True)
    running.add_argument("--source", type=Path, required=True)
    running.add_argument("--workspace", type=Path, required=True)
    running.add_argument("--setup-dir", type=Path, required=True)
    running.add_argument("--executable", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "generate":
            print(generate(args.output, args.setup, args.bundle, override_file=args.override_file))
        elif args.command == "setup":
            print(setup(args.setup, args.output, bundle_root=args.bundle,
                        source_root=args.source, inputs_only=args.inputs_only,
                        override_file=args.override_file))
        elif args.command == "examples":
            for name, record in recipes(args.bundle).items():
                print(f"{name}\t{record['capability']}")
        elif args.command == "build":
            print(build(args.bundle, args.source, args.workspace, args.setup_dir,
                        args.output, args.profile))
        elif args.command == "run":
            print(run(args.bundle, args.source, args.workspace, args.setup_dir,
                      args.executable))
    except (SetupError, RuntimeError, OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
