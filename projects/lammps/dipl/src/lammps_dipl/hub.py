"""Project-specific setup callback using the shared Hub runtime."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil

from snt_hub_runtime import HubSetupError, ProjectBundle, SetupContext, prepare_setup

from .generator import ROOT, generate


SetupError = HubSetupError


def recipes(bundle_root: Path = ROOT) -> dict:
    return ProjectBundle.load(Path(bundle_root).resolve().parent).setups


def setup(name: str, output: Path, *, bundle_root: Path = ROOT,
          source_root: Path | None = None, inputs_only: bool = False,
          override_file: Path | None = None) -> Path:
    bundle_root = Path(bundle_root).resolve()
    bundle = ProjectBundle.load(bundle_root.parent)
    source = Path(source_root).resolve() if source_root else bundle.root / "source"
    override = Path(override_file).resolve() if override_file else None
    if override is not None and not override.is_file():
        raise SetupError(f"Override file does not exist: {override}")
    digest = sha256(override.read_bytes()).hexdigest() if override else None

    def render(context: SetupContext) -> None:
        if override is not None and sha256(override.read_bytes()).hexdigest() != digest:
            raise SetupError("Override changed while preparing the setup")
        generate(context.stage, name, bundle_root, override)
        if override is not None:
            shutil.copyfile(override, context.stage / "input-overrides.dip")
            if sha256((context.stage / "input-overrides.dip").read_bytes()).hexdigest() != digest:
                raise SetupError("Recorded override differs from the evaluated input")

    return prepare_setup(bundle, name, output, source_root=source, render=render,
                         prepare_inputs=lambda _context: None, inputs_only=inputs_only,
                         input_provenance=({"override_file": "input-overrides.dip",
                                            "override_sha256": digest} if digest else None))
