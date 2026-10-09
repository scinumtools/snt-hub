"""Common adapter command line contract used by SNT Hub projects."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from .setup import HubSetupError


def adapter_main(*, description: str, root: Path, default_setup: str,
                 generate: Callable, setup: Callable, recipes: Callable,
                 build: Callable[[argparse.Namespace], Path],
                 run: Callable[[argparse.Namespace], Path],
                 generate_output_default: Path | None = None,
                 build_requires_setup: bool = False) -> None:
    parser = argparse.ArgumentParser(description=description)
    sub = parser.add_subparsers(dest="command", required=True)
    generated = sub.add_parser("generate")
    generated.add_argument("--setup", default=default_setup)
    generated.add_argument("--output", type=Path, required=generate_output_default is None,
                           default=generate_output_default)
    generated.add_argument("--bundle", type=Path, default=root)
    generated.add_argument("--override-file", type=Path)
    prepared = sub.add_parser("setup", help="Prepare a complete example or native inputs only")
    prepared.add_argument("--setup", required=True)
    prepared.add_argument("--output", type=Path, required=True)
    prepared.add_argument("--bundle", type=Path, default=root)
    prepared.add_argument("--source", type=Path)
    prepared.add_argument("--inputs-only", action="store_true")
    prepared.add_argument("--override-file", type=Path)
    listed = sub.add_parser("examples", help="List setup capabilities")
    listed.add_argument("--bundle", type=Path, default=root)
    building = sub.add_parser("build")
    building.add_argument("--bundle", type=Path, required=True)
    building.add_argument("--source", type=Path, required=True)
    building.add_argument("--workspace", type=Path, required=True)
    building.add_argument("--setup-dir", type=Path, required=build_requires_setup)
    building.add_argument("--output", type=Path, required=True)
    building.add_argument("--profile", default="local")
    running = sub.add_parser("run")
    running.add_argument("--bundle", type=Path, required=True)
    running.add_argument("--source", type=Path, required=True)
    running.add_argument("--workspace", type=Path, required=True)
    running.add_argument("--setup-dir", type=Path, required=True)
    running.add_argument("--executable", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "generate":
            print(generate(args.output, args.setup, args.bundle, args.override_file))
        elif args.command == "setup":
            print(setup(args.setup, args.output, bundle_root=args.bundle,
                        source_root=args.source, inputs_only=args.inputs_only,
                        override_file=args.override_file))
        elif args.command == "examples":
            for name, record in recipes(args.bundle).items():
                print(f"{name}\t{record['capability']}")
        elif args.command == "build":
            print(build(args))
        elif args.command == "run":
            print(run(args))
    except (HubSetupError, RuntimeError, OSError, ValueError) as exc:
        parser.error(str(exc))
