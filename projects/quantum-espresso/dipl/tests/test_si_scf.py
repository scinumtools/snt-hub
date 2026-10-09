"""Check the first generated PWscf setup against its pinned upstream input."""

from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest

from qe_dipl.generator import load_environment, render_pw, GenerationError
from qe_dipl.hub import SetupError, setup


PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / "source"


def _namelist(text: str, name: str) -> dict[str, str]:
    match = re.search(rf"(?ims)^\s*&{name}\s*\n(.*?)^\s*/", text)
    assert match, f"missing {name} namelist"
    return {
        key.lower(): value.strip().strip("'").lower()
        for key, value in re.findall(r"([a-z_][a-z0-9_]*(?:\(\d+\))?)\s*=\s*([^,\n]+)", match.group(1), re.I)
    }


def _cards(text: str) -> tuple[list[str], list[list[str]], list[list[str]]]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    species = lines[lines.index("ATOMIC_SPECIES") + 1].split()
    positions_start = next(i for i, line in enumerate(lines) if line.startswith("ATOMIC_POSITIONS"))
    positions = [lines[positions_start + i].split() for i in (1, 2)]
    k_start = next(i for i, line in enumerate(lines) if line.startswith("K_POINTS"))
    count = int(lines[k_start + 1])
    kpoints = [lines[k_start + 2 + i].split() for i in range(count)]
    return species, positions, kpoints


def test_generated_input_matches_pinned_reference_semantically(tmp_path: Path) -> None:
    output = setup("si_scf", tmp_path / "run")
    generated = (output / "pw.in").read_text()
    reference = (SOURCE / "test-suite/pw_scf/scf-ncpp.in").read_text()
    for section in ("control", "system", "electrons"):
        actual = _namelist(generated, section)
        expected = _namelist(reference, section)
        for key, value in expected.items():
            if key in ("pseudo_dir", "outdir"):
                continue
            if key in ("ibrav", "nat", "ntyp", "celldm(1)", "ecutwfc"):
                assert float(actual[key]) == float(value)
            else:
                assert actual[key] == value
    actual_species, actual_positions, actual_kpoints = _cards(generated)
    expected_species, expected_positions, expected_kpoints = _cards(reference)
    assert actual_species[0::2] == expected_species[0::2]
    assert float(actual_species[1]) == float(expected_species[1])
    assert actual_positions[0][0] == expected_positions[0][0]
    assert actual_positions[1][0] == expected_positions[1][0]
    for actual, expected in zip(actual_positions, expected_positions):
        assert list(map(float, actual[1:])) == list(map(float, expected[1:]))
    assert len(actual_kpoints) == len(expected_kpoints)
    for actual, expected in zip(actual_kpoints, expected_kpoints):
        assert list(map(float, actual)) == list(map(float, expected))
    pseudo = output / "pseudo/Si.bhs"
    asset = json.loads((PROJECT / "setups.json").read_text())["setups"]["si_scf"]["pseudo_assets"][0]
    assert sha256(pseudo.read_bytes()).hexdigest() == asset["sha256"]
    assert (output / "environment.diph5").is_file()
    lock = json.loads((output / "setup-lock.json").read_text())
    assert lock["source_revision"] == json.loads((PROJECT / "project.json").read_text())["source_revision"]


def test_override_changes_input_and_is_recorded(tmp_path: Path) -> None:
    override = tmp_path / "tuning.dip"
    override.write_text("system.ecutwfc = 16.0\n")
    output = setup("si_scf", tmp_path / "tuned", override_file=override)
    assert float(_namelist((output / "pw.in").read_text(), "system")["ecutwfc"]) == 16.0
    assert (output / "input-overrides.dip").read_bytes() == override.read_bytes()
    lock = json.loads((output / "setup-lock.json").read_text())
    assert lock["inputs"]["override_sha256"] == sha256(override.read_bytes()).hexdigest()


def test_invalid_structure_and_unreviewed_pseudo_fail(tmp_path: Path) -> None:
    override = tmp_path / "bad-structure.dip"
    override.write_text("system.nat = 3\n")
    with pytest.raises(GenerationError, match="ATOMIC_POSITIONS"):
        render_pw(load_environment(override_file=override))
    override.write_text('structure.species[0].pseudo_file = "other.UPF"\n')
    target = tmp_path / "bad-asset"
    with pytest.raises(SetupError, match="bundled pseudo"):
        setup("si_scf", target, override_file=override)
    assert not target.exists()


def test_setup_from_local_workspace_layout(tmp_path: Path) -> None:
    workspace = tmp_path / "qe-study"
    workspace.mkdir()
    for name in ("project.json", "setups.json"):
        shutil.copyfile(PROJECT / name, workspace / name)
    shutil.copytree(PROJECT / "dipl", workspace / "dipl")
    (workspace / "source").symlink_to(SOURCE, target_is_directory=True)
    output = workspace / "runs" / "si_scf"
    env = {**os.environ, "PYTHONPATH": os.pathsep.join((
            str(PROJECT / "dipl/src"), str(PROJECT.parents[1] / "hub/src"),
            os.environ.get("PYTHONPATH", ""),
        ))}
    command = [sys.executable, "-m", "qe_dipl", "setup", "--bundle", str(workspace / "dipl"),
               "--source", str(workspace / "source")]
    result = subprocess.run(
        [*command, "--setup", "si_scf", "--output", str(output)],
        cwd=workspace, capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, result.stderr
    assert (output / "pw.in").is_file()
    assert (output / "pseudo/Si.bhs").is_file()
    assert json.loads((output / "setup-lock.json").read_text())["source_revision"] == json.loads(
        (workspace / "project.json").read_text())["source_revision"]

    inputs = workspace / "runs" / "scf_gamma"
    result = subprocess.run(
        [*command, "--setup", "scf_gamma", "--inputs-only", "--output", str(inputs)],
        cwd=workspace, capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, result.stderr
    assert (inputs / "pw.in").is_file()
    assert not (inputs / "pseudo").exists()
    assert json.loads((inputs / "setup-lock.json").read_text())["source_revision"] == json.loads(
        (workspace / "project.json").read_text())["source_revision"]
