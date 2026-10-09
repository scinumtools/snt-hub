"""Common setup workflow; participating projects provide rendering callbacks."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from typing import Callable


class HubSetupError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProjectBundle:
    root: Path
    record: dict
    setups: dict[str, dict]
    workspace_lock: dict | None = None

    @classmethod
    def load(cls, project_root: Path) -> "ProjectBundle":
        root = Path(project_root).resolve()
        record = json.loads((root / "project.json").read_text())
        if not isinstance(record.get("id"), str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", record["id"]):
            raise HubSetupError("Invalid project ID")
        declared = record.get("hub", {}).get("setup_manifest")
        if declared:
            relative = Path(declared)
            expected = Path("projects") / record["id"] / "setups.json"
            if relative != expected:
                raise HubSetupError("Setup manifest must name this project's setups.json")
        manifest = json.loads((root / "setups.json").read_text())
        if manifest.get("schema_version") != 1:
            raise HubSetupError("Unsupported setup manifest schema")
        setups = manifest.get("setups")
        if not isinstance(setups, dict) or not setups:
            raise HubSetupError("Setup manifest must contain named setups")
        workspace_lock = None
        lock_path = root / ".snthub" / "lock.json"
        if lock_path.is_file():
            workspace_lock = json.loads(lock_path.read_text())
            if not isinstance(workspace_lock, dict) or workspace_lock.get("schema_version") != 1:
                raise HubSetupError("Unsupported workspace lock schema")
            project = workspace_lock.get("project", workspace_lock.get("project_id"))
            if project != record["id"] or workspace_lock.get("source_revision") != record["source_revision"]:
                raise HubSetupError("Workspace lock disagrees with the project record")
            if not re.fullmatch(r"[0-9a-f]{40}", workspace_lock.get("hub_revision", "")):
                raise HubSetupError("Workspace lock requires a full Hub revision")
            expected_dipl = workspace_lock.get("dipl_sha256")
            if expected_dipl is not None and not re.fullmatch(r"[0-9a-f]{64}", expected_dipl):
                raise HubSetupError("Workspace lock has an invalid DIPL digest")
        return cls(root, record, setups, workspace_lock)

    def recipe(self, name: str) -> dict:
        try:
            recipe = self.setups[name]
        except KeyError as exc:
            raise HubSetupError(f"Unknown {self.record['id']} setup {name!r}") from exc
        if recipe.get("capability") not in {"complete", "native-inputs-only"}:
            raise HubSetupError(f"Invalid capability for {name}")
        return recipe


@dataclass(frozen=True)
class SetupContext:
    bundle: ProjectBundle
    name: str
    recipe: dict
    source_root: Path
    stage: Path
    inputs_only: bool


def _pinned_revision(source_root: Path, expected: str) -> str:
    try:
        actual = subprocess.check_output(
            ["git", "-C", str(source_root), "rev-parse", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise HubSetupError(f"Source is missing or is not a Git checkout: {source_root}") from exc
    if actual != expected:
        raise HubSetupError(f"Source revision {actual} does not match pinned revision {expected}")
    return actual


def _dipl_digest(bundle: Path) -> str | None:
    """Fingerprint model and adapter inputs, excluding generated Python files."""
    if not bundle.is_dir():
        return None
    files = []
    for component in ("pyproject.toml", "examples", "profiles", "src"):
        item = bundle / component
        if item.is_file():
            files.append(item)
        elif item.is_dir():
            files.extend(path for path in item.rglob("*") if path.is_file() and
                         not any(part == "__pycache__" or part.endswith(".egg-info")
                                 for part in path.relative_to(bundle).parts) and
                         path.suffix not in (".pyc", ".pyo"))
    digest = sha256()
    for path in sorted(files, key=lambda item: item.relative_to(bundle).as_posix()):
        relative = path.relative_to(bundle).as_posix().encode()
        contents = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(contents).to_bytes(8, "big"))
        digest.update(contents)
    return digest.hexdigest()


def _source_dirty(source_root: Path) -> bool:
    try:
        return bool(subprocess.check_output(
            ["git", "-C", str(source_root), "status", "--porcelain", "--untracked-files=normal"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip())
    except (OSError, subprocess.CalledProcessError) as exc:
        raise HubSetupError(f"Cannot inspect source checkout: {source_root}") from exc


def prepare_setup(
    bundle: ProjectBundle,
    name: str,
    output: Path,
    *,
    source_root: Path,
    render: Callable[[SetupContext], None],
    prepare_inputs: Callable[[SetupContext], None] | None = None,
    inputs_only: bool = False,
    input_provenance: dict | None = None,
) -> Path:
    """Build in a sibling temporary directory and publish only on success."""
    recipe = bundle.recipe(name)
    if recipe["capability"] != "complete" and not inputs_only:
        raise HubSetupError(f"{name} is native-inputs-only; use --inputs-only")
    if not inputs_only and prepare_inputs is None:
        raise HubSetupError(f"{name} has no initial-input preparation callback")
    output = Path(output).resolve()
    if output.exists():
        raise HubSetupError(f"Output already exists: {output}")
    source_root = Path(source_root).resolve()
    revision = _pinned_revision(source_root, bundle.record["source_revision"])
    source_dirty = _source_dirty(source_root)
    dipl_digest = _dipl_digest(bundle.root / "dipl")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=f".{bundle.record['id']}-setup-", dir=output.parent) as directory:
        stage = Path(directory) / "result"
        stage.mkdir()
        context = SetupContext(bundle, name, recipe, source_root, stage, inputs_only)
        render(context)
        if not inputs_only:
            prepare_inputs(context)
        lock = {
            "schema_version": 1,
            "project": bundle.record["id"],
            "setup": name,
            "capability": "native-inputs-only" if inputs_only else "complete",
            "source_revision": revision,
            "source_dirty": source_dirty,
            "inputs": input_provenance or {},
            "files": sorted(str(path.relative_to(stage)) for path in stage.rglob("*") if path.is_file()),
        }
        if dipl_digest is not None:
            lock["dipl_sha256"] = dipl_digest
        if bundle.workspace_lock is not None:
            lock["hub_revision"] = bundle.workspace_lock["hub_revision"]
            expected_dipl = bundle.workspace_lock.get("dipl_sha256")
            if expected_dipl is None:
                expected_dipl = _dipl_digest(bundle.root / ".snthub" / "hub" /
                                              "projects" / bundle.record["id"] / "dipl")
            if expected_dipl is not None and dipl_digest is not None:
                lock["dipl_modified"] = expected_dipl != dipl_digest
        (stage / "setup-lock.json").write_text(json.dumps(lock, indent=2) + "\n")
        os.replace(stage, output)
    return output
