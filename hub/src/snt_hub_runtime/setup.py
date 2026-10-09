"""Common setup workflow; participating projects provide rendering callbacks."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
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

    @classmethod
    def load(cls, project_root: Path) -> "ProjectBundle":
        root = Path(project_root).resolve()
        record = json.loads((root / "project.json").read_text())
        declared = record.get("hub", {}).get("setup_manifest")
        if declared:
            relative = Path(declared)
            if relative.is_absolute() or ".." in relative.parts or (root.parents[1] / relative).resolve() != root / "setups.json":
                raise HubSetupError("Setup manifest must name this project's setups.json")
        manifest = json.loads((root / "setups.json").read_text())
        if manifest.get("schema_version") != 1:
            raise HubSetupError("Unsupported setup manifest schema")
        setups = manifest.get("setups")
        if not isinstance(setups, dict) or not setups:
            raise HubSetupError("Setup manifest must contain named setups")
        return cls(root, record, setups)

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
    revision = None if inputs_only else _pinned_revision(source_root, bundle.record["source_revision"])
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
            "inputs": input_provenance or {},
            "files": sorted(str(path.relative_to(stage)) for path in stage.rglob("*") if path.is_file()),
        }
        (stage / "setup-lock.json").write_text(json.dumps(lock, indent=2) + "\n")
        os.replace(stage, output)
    return output
