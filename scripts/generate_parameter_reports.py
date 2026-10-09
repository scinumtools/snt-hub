"""Generate checked-in Arepo parameter references with SNT's Brief++ reporter."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "projects" / "arepo"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("setups", nargs="*", help="Setup IDs; default: every Arepo setup")
    args = parser.parse_args()

    record = json.loads((PROJECT / "project.json").read_text())
    recipes = json.loads((PROJECT / "setups.json").read_text())["setups"]
    names = args.setups or sorted(recipes)
    unknown = sorted(set(names) - set(recipes))
    if unknown:
        parser.error("unknown Arepo setups: " + ", ".join(unknown))

    destination = PROJECT / "docs" / "parameters"
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        dipfile = PROJECT / "dipl" / "examples" / name / "DIPfile"
        if not dipfile.is_file():
            raise FileNotFoundError(dipfile)
        output = destination / f"{name}.html"
        subprocess.run(
            [
                "snt", "report", "--project", str(dipfile.relative_to(ROOT)),
                "--format", "html", "--title", f"Arepo · {name.replace('_', ' ').title()} parameters",
                "--date", record["reviewed_on"], "--output", str(output),
            ],
            cwd=ROOT,
            check=True,
        )
        # The reporter can include absolute source paths for schemas outside
        # the DIPfile directory. Keep published references repository-relative.
        html = output.read_text()
        output.write_text(html.replace(f"{ROOT}/", ""))
        print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
