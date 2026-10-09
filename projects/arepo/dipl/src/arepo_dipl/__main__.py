from pathlib import Path

from snt_hub_runtime.cli import adapter_main

from .generator import ROOT, generate
from .hub import recipes, setup
from .workflow import build, run


def main() -> None:
    adapter_main(
        description="Generate Arepo configuration from semantic DIPL.",
        root=ROOT, default_setup="cosmological_star_formation",
        generate=lambda output, name, bundle, override: generate(
            output, name, bundle, override_file=override),
        setup=setup, recipes=recipes,
        build=lambda args: build(args.bundle, args.source, args.workspace,
                                 args.setup_dir, args.output, args.profile),
        run=lambda args: run(args.bundle, args.source, args.workspace,
                             args.setup_dir, args.executable),
        generate_output_default=Path("generated"), build_requires_setup=True,
    )


if __name__ == "__main__":
    main()
