from snt_hub_runtime.cli import adapter_main

from .generator import ROOT, generate
from .hub import recipes, setup


def main() -> None:
    adapter_main(description="Prepare OpenFOAM tutorial cases from DIPL",
                 root=ROOT, default_setup="cavity_ico", generate=generate,
                 setup=setup, recipes=recipes)


if __name__ == "__main__":
    main()
