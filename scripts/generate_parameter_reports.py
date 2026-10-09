"""Generate checked-in Arepo parameter references with SNT's Brief++ reporter."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("setups", nargs="*", help="Setup IDs; default: every setup in the selected project")
    parser.add_argument("--project", default="arepo", help="Project ID (default: arepo)")
    parser.add_argument("--snt", default="snt", help="SNT executable to use (default: snt on PATH)")
    args = parser.parse_args()

    project_id = args.project
    if not project_id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in project_id):
        parser.error("project ID must contain lowercase letters, digits, or hyphens")
    project = ROOT / "projects" / project_id

    record = json.loads((project / "project.json").read_text())
    recipes = json.loads((project / "setups.json").read_text())["setups"]
    names = args.setups or sorted(recipes)
    unknown = sorted(set(names) - set(recipes))
    if unknown:
        parser.error(f"unknown {project_id} setups: " + ", ".join(unknown))

    destination = project / "docs" / "parameters"
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        dipfile = project / "dipl" / "examples" / name / "DIPfile"
        if not dipfile.is_file():
            raise FileNotFoundError(dipfile)
        output = destination / f"{name}.html"
        subprocess.run(
            [
                args.snt, "report", "--project", str(dipfile.relative_to(ROOT)),
                "--format", "html", "--title", f"{record['name']} · {name.replace('_', ' ').title()} parameters",
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
