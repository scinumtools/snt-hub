from snt_hub_runtime.cli import adapter_main

from .generator import ROOT, generate
from .hub import recipes, setup


def _unsupported(_args):
    raise ValueError("Castro build and run hooks have not been validated for this bundle")


def main() -> None:
    adapter_main(
        description="Prepare a pinned Castro Sedov input from DIPL",
        root=ROOT, default_setup="sedov_2d_cartesian", generate=generate,
        setup=setup, recipes=recipes, build=_unsupported, run=_unsupported,
    )


if __name__ == "__main__":
    main()
