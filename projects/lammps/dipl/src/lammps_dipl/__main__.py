from snt_hub_runtime.cli import adapter_main

from .generator import ROOT, generate
from .hub import recipes, setup
from .workflow import build, run


def main() -> None:
    adapter_main(
        description="Prepare LAMMPS LJ inputs from DIPL",
        root=ROOT, default_setup="lj_melt",
        generate=generate, setup=setup, recipes=recipes,
        build=lambda args: build(args.bundle, args.source, args.workspace,
                                 args.output, args.profile, args.setup_dir),
        run=lambda args: run(args.bundle, args.source, args.workspace,
                             args.setup_dir, args.executable),
    )


if __name__ == "__main__":
    main()
