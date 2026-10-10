"""Export SNT schema hierarchies, rebuilding only changed DIPfile projects."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE_VERSION = 1
FILE_ENTRY = re.compile(r'^\s*(?:file|filepath)\s*=\s*"([^"\n]+)"\s*(?:#.*)?$', re.MULTILINE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snt_executable(value: str) -> Path:
    found = shutil.which(value)
    if not found:
        raise FileNotFoundError(f"SNT executable not found: {value}")
    return Path(found).resolve(strict=True)


def input_fingerprint(dipfile: Path, executable_hash: str, generator_hash: str) -> str:
    """Hash the manifest and all registered files, including shared schemas."""
    manifest = dipfile.read_text()
    dependencies = {dipfile}
    for relative in FILE_ENTRY.findall(manifest):
        dependency = (dipfile.parent / relative).resolve(strict=True)
        if not dependency.is_file():
            raise ValueError(f"DIPfile dependency is not a file: {dependency}")
        dependencies.add(dependency)
    digest = hashlib.sha256()
    digest.update(f"schema-export/{STATE_VERSION}\0{executable_hash}\0{generator_hash}\0".encode())
    for path in sorted(dependencies):
        digest.update(str(path.relative_to(ROOT)).encode())
        digest.update(b"\0")
        digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def load_state(path: Path) -> dict:
    if not path.is_file():
        return {"version": STATE_VERSION, "setups": {}}
    try:
        state = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {"version": STATE_VERSION, "setups": {}}
    if state.get("version") != STATE_VERSION or not isinstance(state.get("setups"), dict):
        return {"version": STATE_VERSION, "setups": {}}
    return state


def write_atomic(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            stream.write(content)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    temporary.replace(path)


def generate(project_id: str, names: list[str], snt: str, force: bool = False) -> tuple[int, int]:
    project = ROOT / "projects" / project_id
    destination = project / "docs" / "schemas"
    destination.mkdir(parents=True, exist_ok=True)
    state_path = destination / ".generation-state"
    state = load_state(state_path)
    executable = snt_executable(snt)
    executable_hash = sha256_file(executable)
    generator_hash = sha256_file(Path(__file__))
    generated = skipped = 0

    for name in names:
        dipfile = project / "dipl" / "examples" / name / "DIPfile"
        fingerprint = input_fingerprint(dipfile, executable_hash, generator_hash)
        output = destination / f"{name}.json"
        previous = state["setups"].get(name, {})
        if (not force and output.is_file() and previous.get("fingerprint") == fingerprint
                and previous.get("output_sha256") == sha256_file(output)):
            print(f"unchanged {output.relative_to(ROOT)}", flush=True)
            skipped += 1
            continue

        result = subprocess.run(
            [str(executable), "dip", "schemas", "--project", str(dipfile.relative_to(ROOT)), "--format", "json"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        hierarchy = json.loads(result.stdout)
        if hierarchy.get("schema") != "snt-schema-hierarchy/1" or not hierarchy.get("definitions_available"):
            raise ValueError(f"Expected a live SNT schema hierarchy for {project_id}/{name}")
        write_atomic(output, json.dumps(hierarchy, ensure_ascii=False, separators=(",", ":")) + "\n")
        state["setups"][name] = {"fingerprint": fingerprint, "output_sha256": sha256_file(output)}
        write_atomic(state_path, json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n")
        print(f"generated {output.relative_to(ROOT)}", flush=True)
        generated += 1
    return generated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("setups", nargs="*", help="Setup IDs; default: every setup in the selected project")
    parser.add_argument("--project", required=True, help="Project ID")
    parser.add_argument("--snt", default="snt", help="SNT executable (default: snt on PATH)")
    parser.add_argument("--force", action="store_true", help="Regenerate even when inputs match the cached export")
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
    generated, skipped = generate(project_id, names, args.snt, args.force)
    print(f"{project_id}: {generated} generated, {skipped} unchanged")


if __name__ == "__main__":
    main()
