"""Checks for the packaged entry point that SNT Hub can invoke."""

import json
from hashlib import sha256
import subprocess
import sys

import h5py
import pytest

from arepo_dipl.generator import ROOT
from arepo_dipl.hub import SetupError, recipes, setup


def test_recipe_inventory_matches_dipl_manifests():
    assert set(recipes()) == {path.parent.name for path in (ROOT / "examples").glob("*/DIPfile")}
    assert recipes()["mhd_shock_tube"]["capability"] == "complete"


def test_cli_generation_from_another_directory(tmp_path):
    output = tmp_path / "generated"
    result = subprocess.run(
        [sys.executable, "-m", "arepo_dipl", "generate", "--bundle", str(ROOT),
         "--setup", "alfven_wave_1d", "--output", str(output)],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    for name in ("Config.sh", "param.txt", "environment.diph5"):
        assert (output / name).is_file()


def test_complete_setup_creates_matching_ic_and_lock(tmp_path):
    output = tmp_path / "mhd"
    assert setup("mhd_shock_tube", output) == output
    for name in ("Config.sh", "param.txt", "environment.diph5", "IC.hdf5", "setup-lock.json"):
        assert (output / name).is_file()
    with h5py.File(output / "IC.hdf5") as handle:
        assert float(handle["Header"].attrs["BoxSize"]) == 2.5
    lock = json.loads((output / "setup-lock.json").read_text())
    assert lock["capability"] == "complete"
    assert lock["source_revision"] == "351aa8111a32e2e7433866bf8367ab7eba155d39"
    with pytest.raises(SetupError, match="already exists"):
        setup("mhd_shock_tube", output)
    assert (output / "IC.hdf5").is_file()


def test_setup_command_accepts_bundle_and_source_paths(tmp_path):
    output = tmp_path / "prepared"
    result = subprocess.run(
        [sys.executable, "-m", "arepo_dipl", "setup", "--bundle", str(ROOT),
         "--source", str(ROOT.parent / "source"), "--setup", "mhd_shock_tube",
         "--output", str(output)],
        cwd=tmp_path, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (output / "IC.hdf5").is_file()


def test_unreviewed_ic_requires_explicit_inputs_only(tmp_path):
    output = tmp_path / "alfven"
    with pytest.raises(SetupError, match="native-inputs-only"):
        setup("alfven_wave_1d", output)
    assert not output.exists()
    setup("alfven_wave_1d", output, inputs_only=True)
    assert (output / "Config.sh").is_file()
    assert not (output / "IC.hdf5").exists()


def test_per_run_override_changes_native_input_and_is_recorded(tmp_path):
    override = tmp_path / "tuning.dip"
    override.write_text("resources.wall_clock.limit = 1800 s\nhydrodynamics.courant_factor = 0.25\n")
    output = tmp_path / "tuned"
    setup("mhd_shock_tube", output, override_file=override)
    assert "TimeLimitCPU" in (output / "param.txt").read_text()
    assert any(line.split() == ["TimeLimitCPU", "1800"] for line in (output / "param.txt").read_text().splitlines())
    assert (output / "input-overrides.dip").read_bytes() == override.read_bytes()
    lock = json.loads((output / "setup-lock.json").read_text())
    assert lock["inputs"]["override_sha256"] == sha256(override.read_bytes()).hexdigest()


def test_ic_incompatible_override_does_not_publish(tmp_path):
    override = tmp_path / "tuning.dip"
    override.write_text("simulation.domain.box.size = 3 arepo_length\n")
    output = tmp_path / "mismatch"
    with pytest.raises(SetupError, match="not approved for this complete IC recipe"):
        setup("mhd_shock_tube", output, override_file=override)
    assert not output.exists()
