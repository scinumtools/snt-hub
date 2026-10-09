"""Check that published project records agree with their bundled inputs."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_project(project: Path) -> list[str]:
    issues: list[str] = []
    name = project.name

    def check(condition: bool, message: str) -> None:
        if not condition:
            issues.append(f"{name}: {message}")

    record = json.loads((project / "project.json").read_text())
    manifest = json.loads((project / "setups.json").read_text())
    check(record.get("id") == name, "project ID differs from its directory")
    check(record.get("schema_version") == 1, "unsupported project schema")
    check(manifest.get("schema_version") == 1, "unsupported setup schema")
    hub = record.get("hub", {})
    prefix = f"projects/{name}"
    for field, expected in (("setup_manifest", f"{prefix}/setups.json"),
                            ("adapter_package", f"{prefix}/dipl"),
                            ("runtime_package", "hub"),
                            ("fetch_command", f"snt hub fetch {name}")):
        check(hub.get(field) == expected, f"hub.{field} must be {expected!r}")
    check(record.get("source_path") == f"{prefix}/source", "source_path differs from source submodule")
    check(record.get("adapter_path") == f"{prefix}/dipl", "adapter_path differs from DIPL package")

    source_entry = subprocess.run(
        ["git", "ls-files", "--stage", "--", f"{prefix}/source"],
        cwd=ROOT, text=True, capture_output=True, check=True,
    ).stdout.strip()
    parts = source_entry.split()
    check(len(parts) == 4 and parts[0] == "160000", "source is not an indexed Git submodule")
    if len(parts) == 4:
        check(record.get("source_revision") == parts[1], "source_revision differs from the submodule pin")

    setups = manifest.get("setups", {})
    check(isinstance(setups, dict) and bool(setups), "setups must be a nonempty object")
    if not isinstance(setups, dict):
        return issues
    setup_command = hub.get("setup_command", "")
    command_parts = setup_command.split() if isinstance(setup_command, str) else []
    check(len(command_parts) == 4 and command_parts[:3] == ["snt", "hub", "setup"] and
          command_parts[3] in setups, "hub.setup_command must name a bundled setup")
    example_root = project / "dipl" / "examples"
    report_root = project / "docs" / "parameters"
    example_names = {path.name for path in example_root.iterdir() if path.is_dir()} if example_root.is_dir() else set()
    report_names = {path.stem for path in report_root.glob("*.html")}
    check(set(setups) == example_names, "setup IDs differ from DIPL example directories")
    check(set(setups) == report_names, "setup IDs differ from published parameter reports")
    for setup_name, recipe in setups.items():
        check((example_root / setup_name / "DIPfile").is_file(), f"{setup_name} has no DIPfile")
        check(isinstance(recipe, dict) and recipe.get("capability") in
              {"complete", "native-inputs-only"}, f"{setup_name} has an invalid capability")
        check(isinstance(recipe, dict) and isinstance(recipe.get("source_example"), str),
              f"{setup_name} has no source_example")
    return issues


def main() -> int:
    projects = sorted(path for path in (ROOT / "projects").iterdir()
                      if path.is_dir() and (path / "project.json").is_file())
    issues = [issue for project in projects for issue in check_project(project)]
    if issues:
        print("\n".join(issues), file=sys.stderr)
        return 1
    print(f"Checked {len(projects)} project bundles and their setup reports.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
