import json
from pathlib import Path

import pytest
from scinumtools3.dip import Environment, run_adapter_snapshot

from castro_dipl.generator import CastroAdapter, REFERENCES, ROOT, load_environment, render_inputs
from castro_dipl.hub import setup


SOURCE = ROOT.parent / "source"


@pytest.mark.parametrize("example", sorted(REFERENCES))
def test_default_input_matches_pinned_sedov_reference(example):
    reference = (SOURCE / REFERENCES[example]).read_text()
    assert render_inputs(load_environment(example), reference) == reference


@pytest.mark.parametrize("example", sorted(REFERENCES))
def test_complete_setup_records_source_and_writes_native_input(example, tmp_path):
    output = setup(example, tmp_path / "run")
    assert (output / "inputs").read_text() == (SOURCE / REFERENCES[example]).read_text()
    assert (output / "environment.diph5").is_file()
    lock = json.loads((output / "setup-lock.json").read_text())
    assert lock["capability"] == "complete"
    assert lock["source_revision"] == "371ba40de0ef71963fa8f185d45c7d54e84ec041"
    assert "inputs" in lock["files"]


def test_override_changes_only_modeled_lines(tmp_path):
    override = tmp_path / "override.dip"
    override.write_text("blast.explosion_energy = 2.0\nmesh.nx = 64\n")
    output = setup("sedov_2d_cartesian", tmp_path / "run", override_file=override)
    reference = (SOURCE / REFERENCES["sedov_2d_cartesian"]).read_text()
    generated = (output / "inputs").read_text()
    assert "problem.exp_energy = 2" in generated
    assert "amr.n_cell = 64 32" in generated
    assert "problem.exp_energy = 1.0" in reference
    assert "amr.n_cell           = 32   32" in reference
    assert (output / "input-overrides.dip").read_text() == override.read_text()


@pytest.mark.parametrize("example,axis,expected", [
    ("sedov_1d_spherical", "x", "amr.n_cell = 64"),
    ("sedov_3d_cartesian", "z", "amr.n_cell = 32 32 64"),
])
def test_grid_override_follows_example_dimension(example, axis, expected, tmp_path):
    override = tmp_path / "grid.dip"
    override.write_text(f"mesh.n{axis} = 64\n")
    output = setup(example, tmp_path / "run", override_file=override)
    assert expected in (output / "inputs").read_text()


def test_missing_reference_key_is_rejected():
    with pytest.raises(ValueError, match="missing"):
        render_inputs(load_environment("sedov_2d_cartesian"), "max_step = 500\n")


@pytest.mark.parametrize("example", sorted(REFERENCES))
def test_snapshot_records_and_replays_native_mapping(example, tmp_path):
    first = setup(example, tmp_path / "first")
    snapshot = first / "environment.diph5"
    loaded = Environment()
    loaded.load(snapshot)
    assert loaded.output_plan is not None
    dimensions = 1 if "1d" in example else 3 if "3d" in example else 2
    expected = {"run.max_step", "run.stop_time", "mesh.max_level", "mesh.regrid_interval",
                "hydro.cfl", "hydro.init_shrink", "hydro.change_max", "blast.radius",
                "blast.ambient_pressure", "blast.explosion_energy", "blast.ambient_density",
                "blast.subcells", "eos.gamma"}
    expected.update(f"mesh.n{axis}" for axis in "xyz"[:dimensions])
    assert {mapping.source_path for mapping in loaded.output_plan.mappings} == expected
    replay = tmp_path / "replay"
    run_adapter_snapshot(snapshot, CastroAdapter((SOURCE / REFERENCES[example]).read_text()), replay)
    assert (replay / "inputs").read_bytes() == (first / "inputs").read_bytes()
