"""Run the Hub bundle check, Python suites, and static site build."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_SOURCES = (
    ROOT / "hub" / "src",
    ROOT / "projects" / "arepo" / "dipl" / "src",
    ROOT / "projects" / "quantum-espresso" / "dipl" / "src",
    ROOT / "projects" / "lammps" / "dipl" / "src",
)
PYTHON_TESTS = (
    "hub/tests",
    "projects/arepo/dipl/tests",
    "projects/quantum-espresso/dipl/tests",
    "projects/lammps/dipl/tests",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snt-python-dir", type=Path,
                        help="Optional directory containing a locally built scinumtools3 Python package")
    args = parser.parse_args()
    sources = [*PYTHON_SOURCES]
    if args.snt_python_dir is not None:
        candidate = args.snt_python_dir.resolve()
        if not (candidate / "scinumtools3").is_dir():
            parser.error(f"No scinumtools3 package in {candidate}")
        sources.append(candidate)
    env = os.environ.copy()
    python_path = [str(path) for path in sources]
    if env.get("PYTHONPATH"):
        python_path.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(python_path)
    steps = (
        ("Bundle consistency", [sys.executable, "scripts/check_project_bundles.py"], ROOT),
        ("Python tests", [sys.executable, "-m", "pytest", "-q", *PYTHON_TESTS], ROOT),
        ("Website build", ["npm", "run", "build"], ROOT / "website"),
    )
    for label, command, cwd in steps:
        print(f"\n== {label} ==", flush=True)
        try:
            status = subprocess.run(command, cwd=cwd, env=env, check=False).returncode
        except OSError as exc:
            print(f"Cannot run {command[0]}: {exc}", file=sys.stderr)
            return 1
        if status:
            return status
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
