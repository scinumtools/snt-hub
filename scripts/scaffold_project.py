"""Create a non-published starter tree for a new SNT Hub project."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROJECT_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SETUP_ID = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+)*$")


def parse_setup(value: str) -> tuple[str, str]:
    setup_id, separator, source_example = value.partition("=")
    if not separator or not SETUP_ID.fullmatch(setup_id):
        raise argparse.ArgumentTypeError(
            "setup must be ID=SOURCE_EXAMPLE, with a lowercase ID using letters, digits, and underscores"
        )
    if not source_example.strip() or "\n" in source_example:
        raise argparse.ArgumentTypeError("SOURCE_EXAMPLE must be a nonempty path or reference")
    return setup_id, source_example.strip()


def json_text(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def render_files(project_id: str, name: str, source_url: str,
                 source_revision: str, setups: list[tuple[str, str]]) -> dict[str, str]:
    package = project_id.replace("-", "_") + "_dipl"
    adapter_name = project_id + "-dipl"
    setup_records = {
        setup_id: {
            "capability": "native-inputs-only",
            "source_example": source_example,
            "description": "TODO: describe this scientific example and its input prerequisites.",
        }
        for setup_id, source_example in setups
    }
    project_record = {
        "schema_version": 1,
        "id": project_id,
        "name": name,
        "summary": "TODO: concise description of the scientific code and this Hub integration.",
        "presentation": {
            "about": "TODO: explain what the code simulates, in its own scientific context.",
            "rationale": "TODO: explain why these examples are useful for the Hub integration.",
            "official_page": source_url,
            "official_label": f"Explore {name}",
        },
        "scope": "TODO: define exactly which parameters and examples are modeled.",
        "integration_mode": "External adapter",
        "hub": {
            "status": "TODO: choose the verified Hub status",
            "setup_manifest": f"projects/{project_id}/setups.json",
            "runtime_package": "hub",
            "adapter_package": f"projects/{project_id}/dipl",
            "adapter_executable": adapter_name,
            "adapter_protocol": 1,
            "output_plan": False,
            "fetch_command": f"snt hub fetch {project_id}",
            "setup_command": f"snt hub setup {setups[0][0]}",
        },
        "support": "independent",
        "validation": "prototype",
        "validation_qualifier": "TODO: state what has actually been tested and where.",
        "source_url": source_url,
        "source_path": f"projects/{project_id}/source",
        "source_revision": source_revision,
        "adapter_url": f"https://github.com/scinumtools/snt-hub/tree/main/projects/{project_id}/dipl",
        "adapter_path": f"projects/{project_id}/dipl",
        "adapter_origin_url": None,
        "adapter_revision": None,
        "verification": {"date": "TODO", "scinumtools3": "TODO", "tests_passed": 0},
        "evidence": [],
        "limitations": "TODO: state which native inputs, platforms, and scientific results are not covered.",
        "reviewed_on": "TODO",
    }

    files: dict[str, str] = {
        "README.md": f"""# {name}

TODO: describe the project, supported pinned revision, modeled inputs, and evidence.

- Original source: {source_url}
- Pinned source revision: `{source_revision}`
- DIPL adapter: [`dipl/`](dipl/)
- Setups: {', '.join(f'`{setup_id}`' for setup_id, _ in setups)}

Do not claim maintainer support or validation beyond the evidence recorded here and in `project.json`.
""",
        "project.json.template": json_text(project_record),
        "setups.json.template": json_text({"schema_version": 1, "setups": setup_records}),
        "dipl/README.md": f"""# {name} DIPL adapter

This package is a starter structure. It does not yet generate native inputs.

## Setups

""" + "".join(f"- `{setup_id}`: `{source_example}`\n" for setup_id, source_example in setups) + """

## Implementation checklist

- [ ] Model reviewed parameters, units, constraints, and dependencies in DIPL.
- [ ] Implement a renderer that writes the code's native input format.
- [ ] Add parity tests against the pinned source examples.
- [ ] Implement setup/build/run hooks only when their workflows are verified.
- [ ] Generate parameter and schema reports with `scripts/generate_project_docs.py`.
- [ ] Replace every `TODO` in the project guide and metadata.
""",
        "dipl/pyproject.toml": f"""[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "snt-hub-{project_id}"
version = "0.1.0"
description = "{name} DIPL adapter for SNT Hub"
requires-python = ">=3.10"
dependencies = ["scinumtools3>=0.9.3", "snt-hub-runtime>=0.1.0"]

[project.optional-dependencies]
test = ["pytest"]

[tool.setuptools.packages.find]
where = ["src"]
""",
        "dipl/profiles/schemas/README.md": "# Reusable DIPL schemas\n\nAdd reviewed, coherent schema definitions here. Keep example-specific values in `examples/<setup>/`.\n",
        f"dipl/src/{package}/__init__.py": f'"""DIPL integration package for {name}."""\n',
        f"dipl/src/{package}/generator.py": '''"""Project-specific native input renderer."""

from pathlib import Path


def generate(output: Path, setup: str, bundle_root: Path, override_file: Path | None = None) -> Path:
    """Evaluate one DIPL setup and render its native input files.

    Implement this only after the DIPL nodes and native mappings have been reviewed.
    Compare generated files with the corresponding pinned upstream examples.
    """
    raise NotImplementedError("Implement the reviewed native input renderer")
''',
        "dipl/tests/README.md": "Add tests for native input parity, supported overrides, output paths, and setup provenance. Do not claim parity until the tests compare against the pinned source examples.\n",
        "docs/README.md": "Generated parameter references and schema hierarchies will live here after each DIPL setup has been implemented. Use `scripts/generate_project_docs.py` to create them.\n",
    }
    for setup_id, source_example in setups:
        directory = f"dipl/examples/{setup_id}"
        files[f"{directory}/DIPfile"] = (
            "# Register shared schemas before example settings.\n"
            "code[]\n"
            "  file = \"settings.dip\"\n"
        )
        files[f"{directory}/settings.dip"] = (
            f"# TODO: model reviewed parameters for {source_example}.\n"
            "# Add DIPL nodes only when their meaning, units, and native mapping are understood.\n"
        )
    return files


def create_scaffold(output: Path, files: dict[str, str]) -> list[Path]:
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"output directory is not empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    written = []
    for relative, content in files.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="lowercase project ID, for example my-code")
    parser.add_argument("--name", required=True, help="display name of the scientific code")
    parser.add_argument("--source-url", required=True, help="canonical upstream source or project URL")
    parser.add_argument("--source-revision", required=True, help="full upstream commit to pin")
    parser.add_argument("--setup", action="append", type=parse_setup, required=True,
                        metavar="ID=SOURCE_EXAMPLE", help="reviewed setup ID and its upstream input reference; repeatable")
    parser.add_argument("--output", type=Path,
                        help="destination (default: projects/_drafts/<id>); must be empty or absent")
    args = parser.parse_args()

    if not PROJECT_ID.fullmatch(args.id):
        parser.error("--id must use lowercase letters, digits, and single hyphens")
    if not args.name.strip() or not args.source_url.strip() or not args.source_revision.strip():
        parser.error("--name, --source-url, and --source-revision must not be empty")
    setup_ids = [setup_id for setup_id, _ in args.setup]
    duplicates = sorted({setup_id for setup_id in setup_ids if setup_ids.count(setup_id) > 1})
    if duplicates:
        parser.error("duplicate setup IDs: " + ", ".join(duplicates))
    output = (args.output or ROOT / "projects" / "_drafts" / args.id).resolve()
    try:
        written = create_scaffold(
            output,
            render_files(args.id, args.name.strip(), args.source_url.strip(),
                         args.source_revision.strip(), args.setup),
        )
    except (FileExistsError, OSError) as exc:
        print(f"Cannot create scaffold: {exc}", file=sys.stderr)
        return 1
    print(f"Created {len(written)} starter files in {output}")
    print("This is a draft: review the TODOs, add the pinned source submodule, then promote the metadata templates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
