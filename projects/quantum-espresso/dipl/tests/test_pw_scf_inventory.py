"""Parity and setup checks for all pinned PWscf regression inputs."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

from qe_dipl.hub import SetupError, setup
from qe_dipl.reference import SOURCE, parse_native, render_settings, setup_id


PROJECT = Path(__file__).resolve().parents[2]
SOURCE_INPUTS = sorted(path for path in (SOURCE / "test-suite/pw_scf").glob("*.in")
                       if not path.name.startswith("benchmark"))
RECIPES = json.loads((PROJECT / "setups.json").read_text())["setups"]


def _portable(parsed: dict) -> dict:
    parsed["namelists"]["control"].pop("pseudo_dir", None)
    parsed["namelists"]["control"].pop("outdir", None)
    return parsed


def test_inventory_covers_the_pinned_pw_scf_directory() -> None:
    assert len(SOURCE_INPUTS) == 27
    assert set(RECIPES) == {setup_id(path.name) for path in SOURCE_INPUTS}
    for path in SOURCE_INPUTS:
        name = setup_id(path.name)
        assert RECIPES[name]["source_example"] == f"test-suite/pw_scf/{path.name}"
        assert (PROJECT / "source" / RECIPES[name]["source_example"]).is_file()
        assert (PROJECT / "dipl/examples" / name / "DIPfile").is_file()
        assert (PROJECT / "docs/parameters" / f"{name}.html").is_file()


@pytest.mark.parametrize("source_file", SOURCE_INPUTS, ids=lambda path: path.name)
def test_every_dipl_setup_matches_native_input(source_file: Path, tmp_path: Path) -> None:
    name = setup_id(source_file.name)
    inputs_only = RECIPES[name]["capability"] == "native-inputs-only"
    output = setup(name, tmp_path / name, inputs_only=inputs_only)
    native_file = output / "pw.in"
    assert native_file.is_file()
    assert (output / "environment.diph5").is_file()
    lock = json.loads((output / "setup-lock.json").read_text())
    assert lock["project"] == "quantum-espresso"
    assert lock["setup"] == name
    assert lock["capability"] == RECIPES[name]["capability"]
    assert _portable(parse_native(native_file)) == _portable(parse_native(source_file))
    assert (PROJECT / "dipl/examples" / name / "settings.dip").read_text() == render_settings(
        parse_native(source_file), source_file.name
    )


@pytest.mark.parametrize("name", ["si_scf", "scf_gth"])
def test_complete_setups_stage_checked_pseudopotentials(name: str, tmp_path: Path) -> None:
    output = setup(name, tmp_path / name)
    lock = json.loads((output / "setup-lock.json").read_text())
    assert lock["capability"] == "complete"
    assert lock["source_revision"] == json.loads((PROJECT / "project.json").read_text())["source_revision"]
    for asset in RECIPES[name]["pseudo_assets"]:
        staged = output / "pseudo" / asset["file"]
        assert sha256(staged.read_bytes()).hexdigest() == asset["sha256"]
        assert {"file": asset["file"], "sha256": asset["sha256"]} in lock["inputs"]["pseudopotentials"]


def test_missing_assets_require_inputs_only(tmp_path: Path) -> None:
    with pytest.raises(SetupError, match="native-inputs-only"):
        setup("scf_gamma", tmp_path / "incomplete")
    output = setup("scf_gamma", tmp_path / "inputs", inputs_only=True)
    assert (output / "pw.in").is_file()
    assert not (output / "pseudo").exists()
    assert json.loads((output / "setup-lock.json").read_text())["capability"] == "native-inputs-only"
