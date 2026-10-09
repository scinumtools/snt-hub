"""Arepo-specific rendering and IC recipe for the reusable hub setup runner."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil
import subprocess
import sys

from snt_hub_runtime import HubSetupError, ProjectBundle, SetupContext, prepare_setup

from .generator import ROOT, generate, load_environment
from .rendering import value_at


SetupError = HubSetupError


def project_root(bundle_root: Path = ROOT) -> Path:
    return Path(bundle_root).resolve().parent


def recipes(bundle_root: Path = ROOT) -> dict:
    return ProjectBundle.load(project_root(bundle_root)).setups


def _verify_override(path: Path | None, digest: str | None) -> None:
    if path is not None and sha256(path.read_bytes()).hexdigest() != digest:
        raise SetupError("Override file changed while preparing the setup")


def _render(context: SetupContext, bundle_root: Path, override_file: Path | None, digest: str | None) -> None:
    manifest = bundle_root / "examples" / context.name / "DIPfile"
    if not manifest.is_file():
        raise SetupError(f"Missing DIPL manifest: {manifest}")
    _verify_override(override_file, digest)
    generate(context.stage, context.name, bundle_root, override_file=override_file)
    if override_file is not None:
        shutil.copyfile(override_file, context.stage / "input-overrides.dip")
        _verify_override(override_file, digest)
        if sha256((context.stage / "input-overrides.dip").read_bytes()).hexdigest() != digest:
            raise SetupError("Recorded override copy differs from the evaluated input")


def _prepare_ic(context: SetupContext, bundle_root: Path, override_file: Path | None, digest: str | None) -> None:
    try:
        import h5py
    except ImportError as exc:
        raise SetupError("Complete Arepo setup requires h5py in the adapter environment") from exc
    _verify_override(override_file, digest)
    env = load_environment(context.name, bundle_root, override_file)
    _verify_override(override_file, digest)
    approved = set(context.recipe.get("ic_safe_overrides", []))
    changed = {node.name for node in env.select("?") if node.override}
    unsafe = sorted(changed - approved)
    if unsafe:
        raise SetupError("Override targets are not approved for this complete IC recipe: " + ", ".join(unsafe))
    example = context.source_root / "examples" / context.recipe["source_example"]
    creator = example / context.recipe["ic_creator"]
    if not creator.is_file():
        raise SetupError(f"Missing pinned IC creator: {creator}")
    try:
        subprocess.run([sys.executable, str(creator), str(context.stage)], cwd=example, check=True)
    except subprocess.CalledProcessError as exc:
        raise SetupError(f"IC creator failed for {context.name} with exit code {exc.returncode}") from exc
    ic_file = context.stage / context.recipe["ic_file"]
    if not ic_file.is_file():
        raise SetupError(f"IC creator did not write {ic_file.name}")
    ic_path = value_at(env, "input.initial_conditions.path")
    ic_format = value_at(env, "input.initial_conditions.format")
    if ic_format != 3 or ic_file != context.stage / (ic_path.removeprefix("./") + ".hdf5"):
        raise SetupError("Generated IC path or format does not match the DIPL model")
    with h5py.File(ic_file, "r") as handle:
        box_size = float(handle["Header"].attrs["BoxSize"])
    if abs(box_size - float(value_at(env, "simulation.domain.box.size"))) > 1e-10:
        raise SetupError("IC box size does not match the evaluated DIPL model")


def setup(
    name: str,
    output: Path,
    *,
    bundle_root: Path = ROOT,
    source_root: Path | None = None,
    inputs_only: bool = False,
    override_file: Path | None = None,
) -> Path:
    bundle_root = Path(bundle_root).resolve()
    bundle = ProjectBundle.load(project_root(bundle_root))
    source = Path(source_root).resolve() if source_root else bundle.root / "source"
    override = Path(override_file).resolve() if override_file else None
    if override is not None and not override.is_file():
        raise SetupError(f"Override file does not exist: {override}")
    provenance = ({"override_file": "input-overrides.dip",
                   "override_sha256": sha256(override.read_bytes()).hexdigest()}
                  if override is not None else None)
    digest = provenance["override_sha256"] if provenance else None
    return prepare_setup(
        bundle, name, output,
        source_root=source,
        render=lambda context: _render(context, bundle_root, override, digest),
        prepare_inputs=lambda context: _prepare_ic(context, bundle_root, override, digest),
        inputs_only=inputs_only,
        input_provenance=provenance,
    )
