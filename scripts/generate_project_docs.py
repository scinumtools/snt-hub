"""Generate and validate the parameter and schema documents for Hub projects."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_VERSION = 1
FILE_ENTRY = re.compile(r'^\s*(?:file|filepath)\s*=\s*"([^"\n]+)"\s*(?:#.*)?$', re.MULTILINE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def executable_path(value: str) -> Path:
    found = shutil.which(value)
    if not found:
        raise FileNotFoundError(f"SNT executable not found: {value}")
    return Path(found).resolve(strict=True)


def dependencies(dipfile: Path) -> list[Path]:
    found = {dipfile.resolve(strict=True)}
    for relative in FILE_ENTRY.findall(dipfile.read_text()):
        path = (dipfile.parent / relative).resolve(strict=True)
        if not path.is_file():
            raise ValueError(f"DIPfile dependency is not a file: {path}")
        found.add(path)
    return sorted(found)


def fingerprint(project: Path, dipfile: Path, snt_hash: str, generator_hash: str) -> str:
    digest = hashlib.sha256()
    digest.update(f"project-docs/{STATE_VERSION}\0{snt_hash}\0{generator_hash}\0".encode())
    inputs = [project / "project.json", *dependencies(dipfile)]
    for path in sorted(set(inputs)):
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256(path)))
    return digest.hexdigest()


def read_state(path: Path) -> dict:
    try:
        state = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {"version": STATE_VERSION, "setups": {}}
    if state.get("version") != STATE_VERSION or not isinstance(state.get("setups"), dict):
        return {"version": STATE_VERSION, "setups": {}}
    return state


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(content)
    temporary.replace(path)


def render_documents(snt: Path, project: Path, record: dict, dipfile: Path) -> dict[str, str]:
    setup = dipfile.parent.name
    with tempfile.TemporaryDirectory(prefix="snt-hub-docs-") as directory:
        report_path = Path(directory) / f"{setup}.json"
        subprocess.run(
            [
                str(snt), "report", "--project", str(dipfile.relative_to(ROOT)),
                "--format", "json", "--title", f"{record['name']} · {setup.replace('_', ' ').title()} parameters",
                "--date", record["reviewed_on"], "--output", str(report_path),
            ],
            cwd=ROOT,
            check=True,
        )
        report_text = report_path.read_text().replace(f"{ROOT}/", "")
    report = json.loads(report_text)
    if report.get("schema") != "briefpp/1":
        raise ValueError(f"Unexpected Brief++ document schema for {project.name}/{setup}")
    report_text = json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n"

    hierarchy_result = subprocess.run(
        [str(snt), "dip", "schemas", "--project", str(dipfile.relative_to(ROOT)), "--format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    hierarchy = json.loads(hierarchy_result.stdout)
    if hierarchy.get("schema") != "snt-schema-hierarchy/1" or not hierarchy.get("definitions_available"):
        raise ValueError(f"Expected a live SNT schema hierarchy for {project.name}/{setup}")
    hierarchy_text = json.dumps(hierarchy, ensure_ascii=False, separators=(",", ":")) + "\n"
    return {
        str(project / "docs" / "parameters" / f"{setup}.json"): report_text,
        str(project / "docs" / "schemas" / f"{setup}.json"): hierarchy_text,
    }


def generate(project: Path, setup_names: list[str], snt_value: str, force: bool, check: bool) -> tuple[int, int, list[str]]:
    snt = executable_path(snt_value)
    record = json.loads((project / "project.json").read_text())
    state_path = project / "docs" / ".generation-state"
    state = read_state(state_path)
    snt_hash = sha256(snt)
    generator_hash = sha256(Path(__file__).resolve())
    generated = unchanged = 0
    stale: list[str] = []

    for setup in setup_names:
        dipfile = project / "dipl" / "examples" / setup / "DIPfile"
        if not dipfile.is_file():
            raise FileNotFoundError(dipfile)
        input_hash = fingerprint(project, dipfile, snt_hash, generator_hash)
        previous = state["setups"].get(setup, {})
        outputs = {
            "parameters": project / "docs" / "parameters" / f"{setup}.json",
            "schemas": project / "docs" / "schemas" / f"{setup}.json",
        }
        cached = all(
            outputs[key].is_file()
            and previous.get(key) == sha256(outputs[key])
            for key in outputs
        )
        if not force and cached and previous.get("fingerprint") == input_hash:
            print(f"unchanged {project.name}/{setup}", flush=True)
            unchanged += 1
            continue

        rendered = render_documents(snt, project, record, dipfile)
        changed_paths = []
        for output_name, content in rendered.items():
            output = ROOT / output_name
            if not output.is_file() or output.read_text() != content:
                changed_paths.append(output)

        if check:
            if changed_paths:
                stale.extend(str(path.relative_to(ROOT)) for path in changed_paths)
                print(f"stale {project.name}/{setup}", flush=True)
            else:
                print(f"unchanged {project.name}/{setup}", flush=True)
                unchanged += 1
            continue

        for output_name, content in rendered.items():
            output = ROOT / output_name
            if output in changed_paths:
                atomic_write(output, content)
        state["setups"][setup] = {
            "fingerprint": input_hash,
            "parameters": sha256(outputs["parameters"]),
            "schemas": sha256(outputs["schemas"]),
        }
        atomic_write(state_path, json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n")
        if changed_paths:
            print(f"generated {project.name}/{setup}: " + ", ".join(path.name for path in changed_paths), flush=True)
            generated += 1
        else:
            print(f"updated cache {project.name}/{setup}", flush=True)
            unchanged += 1

    return generated, unchanged, stale


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Project ID; default: every registered project")
    parser.add_argument("--setup", action="append", dest="setups", help="Setup ID (repeatable); default: every selected setup")
    parser.add_argument("--snt", default="snt", help="SNT executable (default: snt on PATH)")
    parser.add_argument("--force", action="store_true", help="Regenerate selected documents regardless of cache")
    parser.add_argument("--check", action="store_true", help="Check that generated documents match current inputs")
    args = parser.parse_args()
    if args.force and args.check:
        parser.error("--force and --check cannot be used together")
    if args.project and any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-" for char in args.project):
        parser.error("project ID must contain lowercase letters, digits, or hyphens")
    if args.setups and not args.project:
        parser.error("--setup requires --project")

    projects = [ROOT / "projects" / args.project] if args.project else sorted(
        path for path in (ROOT / "projects").iterdir() if (path / "project.json").is_file()
    )
    stale: list[str] = []
    for project in projects:
        if not (project / "project.json").is_file():
            parser.error(f"unknown project: {project.name}")
        recipes = json.loads((project / "setups.json").read_text())["setups"]
        setup_names = args.setups or sorted(recipes)
        unknown = sorted(set(setup_names) - set(recipes))
        if unknown:
            parser.error(f"unknown {project.name} setups: " + ", ".join(unknown))
        generated, unchanged, project_stale = generate(
            project, setup_names, args.snt, args.force, args.check
        )
        stale.extend(project_stale)
        print(f"{project.name}: {generated} generated, {unchanged} unchanged")

    if stale:
        print("Generated project documents are stale:", file=sys.stderr)
        print("\n".join(f"  {path}" for path in stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
