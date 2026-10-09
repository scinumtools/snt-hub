"""Arepo-specific rendering and IC recipe for the reusable hub setup runner."""

from __future__ import annotations

from pathlib import Path
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


def _render(context: SetupContext, bundle_root: Path) -> None:
    manifest = bundle_root / "examples" / context.name / "DIPfile"
    if not manifest.is_file():
        raise SetupError(f"Missing DIPL manifest: {manifest}")
    generate(context.stage, context.name, bundle_root)


def _prepare_ic(context: SetupContext, bundle_root: Path) -> None:
    try:
        import h5py
    except ImportError as exc:
        raise SetupError("Complete Arepo setup requires h5py in the adapter environment") from exc
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
    env = load_environment(context.name, bundle_root)
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
) -> Path:
    bundle_root = Path(bundle_root).resolve()
    bundle = ProjectBundle.load(project_root(bundle_root))
    source = Path(source_root).resolve() if source_root else bundle.root / "source"
    return prepare_setup(
        bundle, name, output,
        source_root=source,
        render=lambda context: _render(context, bundle_root),
        prepare_inputs=lambda context: _prepare_ic(context, bundle_root),
        inputs_only=inputs_only,
    )
