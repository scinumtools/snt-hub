"""Regenerate QE's PWscf regression DIPL recipes from the pinned source tree."""

from __future__ import annotations

import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "projects" / "quantum-espresso" / "dipl" / "src"))

from qe_dipl.reference import ROOT as PROJECT, import_all  # noqa: E402


def main() -> None:
    manifest = import_all()
    (PROJECT / "setups.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Imported {len(manifest['setups'])} pinned PWscf inputs")


if __name__ == "__main__":
    main()
