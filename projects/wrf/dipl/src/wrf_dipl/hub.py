"""Project-specific callback using the shared Hub setup runtime."""

from __future__ import annotations

from pathlib import Path

from snt_hub_runtime import ProjectBundle, SetupContext, prepare_setup

from .generator import ROOT, generate


def recipes(bundle_root: Path = ROOT) -> dict:
    return ProjectBundle.load(Path(bundle_root).resolve().parent).setups


def setup(name: str, output: Path, *, bundle_root: Path = ROOT,
          source_root: Path | None = None, inputs_only: bool = False,
          override_file: Path | None = None) -> Path:
    bundle_root = Path(bundle_root).resolve()
    bundle = ProjectBundle.load(bundle_root.parent)
    source = Path(source_root).resolve() if source_root else bundle.root / "source"
    override = Path(override_file).resolve() if override_file else None

    def render(context: SetupContext) -> None:
        generate(context.stage, name, bundle_root, override, context.source_root)

    return prepare_setup(bundle, name, output, source_root=source, render=render,
                         inputs_only=inputs_only, override_file=override)
