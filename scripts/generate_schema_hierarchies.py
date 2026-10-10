"""Export SNT schema hierarchy contracts for published Hub examples."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("setups", nargs="*", help="Setup IDs; default: every setup in the selected project")
    parser.add_argument("--project", required=True, help="Project ID")
    parser.add_argument("--snt", default="snt", help="SNT executable (default: snt on PATH)")
    args = parser.parse_args()

    project_id = args.project
    if not project_id or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in project_id):
        parser.error("project ID must contain lowercase letters, digits, or hyphens")
    project = ROOT / "projects" / project_id
    recipes = json.loads((project / "setups.json").read_text())["setups"]
    names = args.setups or sorted(recipes)
    unknown = sorted(set(names) - set(recipes))
    if unknown:
        parser.error(f"unknown {project_id} setups: " + ", ".join(unknown))

    destination = project / "docs" / "schemas"
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        dipfile = project / "dipl" / "examples" / name / "DIPfile"
        result = subprocess.run(
            [args.snt, "dip", "schemas", "--project", str(dipfile.relative_to(ROOT)), "--format", "json"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        hierarchy = json.loads(result.stdout)
        if hierarchy.get("schema") != "snt-schema-hierarchy/1" or not hierarchy.get("definitions_available"):
            raise ValueError(f"Expected a live SNT schema hierarchy for {project_id}/{name}")
        output = destination / f"{name}.json"
        output.write_text(json.dumps(hierarchy, ensure_ascii=False, separators=(",", ":")) + "\n")
        print(output.relative_to(ROOT), flush=True)


if __name__ == "__main__":
    main()
