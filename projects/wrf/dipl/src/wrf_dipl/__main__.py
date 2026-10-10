from snt_hub_runtime.cli import adapter_main

from .generator import ROOT, generate
from .hub import recipes, setup


def _unsupported(_args):
    raise ValueError("WRF build and run hooks have not been validated for this bundle")


def main() -> None:
    adapter_main(
        description="Prepare pinned WRF idealized-case native inputs from DIPL",
        root=ROOT, default_setup="hill_2d", generate=generate,
        setup=setup, recipes=recipes, build=_unsupported, run=_unsupported,
    )


if __name__ == "__main__":
    main()
