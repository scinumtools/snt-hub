import json
from pathlib import Path
import shutil
import struct

import pytest
from scinumtools3.dip import inspect_table

from wrf_dipl.generator import ROOT, UPSTREAM_CASES, load_environment, render_namelist
from wrf_dipl.hub import setup as prepare_setup


SOURCE = ROOT.parent / "source"


def _sounding_values(text: str) -> list[list[float]]:
    return [[float(token) for token in line.split()]
            for line in text.splitlines() if line.strip()]


def _as_wrf_real(value: float) -> bytes:
    return struct.pack("=f", value)


def test_hill_sounding_profile_is_an_imported_typed_table():
    env = load_environment("hill_2d")
    table = inspect_table(env, "sounding.profile")
    assert [column.name for column in table.columns] == [
        "height", "potential_temperature", "water_vapor_mixing_ratio", "u_wind", "v_wind",
    ]
    assert all(len(env[column.path].value) == 601 for column in table.columns)


@pytest.mark.parametrize("setup", sorted(UPSTREAM_CASES))
def test_pinned_namelist_and_sounding_parity(setup, tmp_path):
    case, assets, _ideal_case = UPSTREAM_CASES[setup]
    upstream = SOURCE / "test" / case
    namelist = upstream / "namelist.input"
    assert render_namelist(load_environment(setup), namelist.read_text(), setup) == namelist.read_text()

    output = tmp_path / setup
    prepare_setup(setup, output, inputs_only=True)
    assert (output / "namelist.input").read_bytes() == namelist.read_bytes()
    for asset in assets:
        if setup == "hill_2d" and asset == "input_sounding":
            generated = _sounding_values((output / asset).read_text())
            reference_bytes = (upstream / asset).read_bytes()
            reference = _sounding_values(reference_bytes.decode())
            assert (output / asset).read_bytes() != reference_bytes
            assert [len(row) for row in generated] == [len(row) for row in reference]
            assert [[_as_wrf_real(value) for value in row] for row in generated] == [
                [_as_wrf_real(value) for value in row] for row in reference
            ]
        else:
            assert (output / asset).read_bytes() == (upstream / asset).read_bytes()
    assert (output / "environment.diph5").is_file()
    lock = json.loads((output / "setup-lock.json").read_text())
    assert lock["capability"] == "native-inputs-only"
    assert lock["source_revision"] == "06d4240ae989cc3e50af412bb472df3d9048783c"


def test_override_changes_native_grid_and_is_recorded(tmp_path):
    override = tmp_path / "grid.dip"
    override.write_text("domains.dx = 1500\n")
    output = tmp_path / "hill"
    prepare_setup("hill_2d", output, inputs_only=True, override_file=override)
    original = (SOURCE / "test/em_hill2d_x/namelist.input").read_text()
    generated = (output / "namelist.input").read_text()
    assert generated == original.replace("dx                                  = 2000,",
                                         "dx                                  = 1500,")
    assert (output / "input-overrides.dip").read_text() == override.read_text()
    assert json.loads((output / "setup-lock.json").read_text())["inputs"]["override_sha256"]


def test_sounding_surface_override_is_written_and_recorded(tmp_path):
    override = tmp_path / "surface.dip"
    override.write_text("sounding.surface.pressure = 1001 hPa\n")
    output = tmp_path / "hill"
    prepare_setup("hill_2d", output, inputs_only=True, override_file=override)
    generated = _sounding_values((output / "input_sounding").read_text())
    assert generated[0][0] == 1001.0
    assert json.loads((output / "setup-lock.json").read_text())["inputs"]["override_sha256"]


def test_incompatible_boundary_override_publishes_no_setup(tmp_path):
    override = tmp_path / "bad.dip"
    override.write_text("bdy_control.periodic_x = true\n")
    output = tmp_path / "invalid"
    with pytest.raises(ValueError, match="cannot also be open"):
        prepare_setup("hill_2d", output, inputs_only=True, override_file=override)
    assert not output.exists()


@pytest.mark.parametrize("setup,override_text,expected", [
    ("hill_2d", "domains.e_sn = 4\n", "x-oriented"),
    ("squall_line_y", "domains.e_we = 4\n", "y-oriented"),
])
def test_2d_orientation_override_is_rejected(setup, override_text, expected, tmp_path):
    override = tmp_path / "bad.dip"
    override.write_text(override_text)
    with pytest.raises(ValueError, match=expected):
        prepare_setup(setup, tmp_path / "invalid", inputs_only=True, override_file=override)
    assert not (tmp_path / "invalid").exists()


def test_inputs_only_choice_is_required(tmp_path):
    output = tmp_path / "hill"
    with pytest.raises(RuntimeError, match="native-inputs-only"):
        prepare_setup("hill_2d", output)
    assert not output.exists()


def test_fetched_workspace_layout(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    for name in ("project.json", "setups.json"):
        shutil.copyfile(ROOT.parent / name, workspace / name)
    shutil.copytree(ROOT, workspace / "dipl", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    output = workspace / "runs" / "hill_2d"
    prepare_setup("hill_2d", output, bundle_root=workspace / "dipl",
                  source_root=SOURCE, inputs_only=True)
    assert (output / "namelist.input").is_file()
    assert json.loads((output / "setup-lock.json").read_text())["project"] == "wrf"
