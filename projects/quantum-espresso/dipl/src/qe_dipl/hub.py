"""QE-specific asset preparation for the shared SNT Hub setup runner."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil

from snt_hub_runtime import HubSetupError, ProjectBundle, SetupContext, prepare_setup

from .generator import ROOT, generate, load_environment, records, value


SetupError = HubSetupError


def recipes(bundle_root: Path = ROOT) -> dict:
    return ProjectBundle.load(Path(bundle_root).resolve().parent).setups


def setup(name: str, output: Path, *, bundle_root: Path = ROOT,
          source_root: Path | None = None, inputs_only: bool = False,
          override_file: Path | None = None) -> Path:
    bundle_root = Path(bundle_root).resolve()
    bundle = ProjectBundle.load(bundle_root.parent)
    recipe = bundle.recipe(name)
    source = Path(source_root).resolve() if source_root else bundle.root / "source"
    override = Path(override_file).resolve() if override_file else None
    if override is not None and not override.is_file():
        raise SetupError(f"Override file does not exist: {override}")
    digest = sha256(override.read_bytes()).hexdigest() if override else None
    provenance: dict = {}
    if override:
        provenance.update({"override_file": "input-overrides.dip", "override_sha256": digest})
    if not inputs_only:
        provenance["pseudopotentials"] = [
            {"file": asset["file"], "sha256": asset["sha256"]}
            for asset in recipe.get("pseudo_assets", [])
        ]

    def check_override() -> None:
        if override is not None and sha256(override.read_bytes()).hexdigest() != digest:
            raise SetupError("Override file changed during setup")

    def render(context: SetupContext) -> None:
        check_override()
        generate(context.stage, context.name, bundle_root, override)
        if override is not None:
            shutil.copyfile(override, context.stage / "input-overrides.dip")
            check_override()

    def prepare_pseudo(context: SetupContext) -> None:
        check_override()
        env = load_environment(context.name, bundle_root, override)
        species = records(env, "structure.species", ("symbol", "mass", "pseudo_file"))
        assets = context.recipe.get("pseudo_assets", [])
        if (value(env, "control.pseudo_dir") != "./pseudo/" or
                [item["pseudo_file"] for item in species] != [asset["file"] for asset in assets]):
            raise SetupError("Complete setup requires the bundled pseudopotentials and ./pseudo/ path")
        for asset in assets:
            if Path(asset["file"]).name != asset["file"]:
                raise SetupError("Pseudopotential entry must be a filename")
            source_file = context.source_root / asset["source"]
            if not source_file.is_file() or sha256(source_file.read_bytes()).hexdigest() != asset["sha256"]:
                raise SetupError(f"Pinned pseudopotential {asset['file']} is missing or its SHA-256 differs")
            destination = context.stage / "pseudo" / asset["file"]
            destination.parent.mkdir(exist_ok=True)
            shutil.copyfile(source_file, destination)
            if sha256(destination.read_bytes()).hexdigest() != asset["sha256"]:
                raise SetupError(f"Staged pseudopotential {asset['file']} differs from the pinned asset")
        (context.stage / value(env, "control.outdir")).mkdir(parents=True, exist_ok=True)
        check_override()

    return prepare_setup(bundle, name, output, source_root=source,
                         render=render, prepare_inputs=prepare_pseudo,
                         inputs_only=inputs_only, input_provenance=provenance)
