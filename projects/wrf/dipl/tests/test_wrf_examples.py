import json
from pathlib import Path
import shutil

import pytest

from wrf_dipl.generator import ROOT, UPSTREAM_CASES, load_environment, render_namelist
from wrf_dipl.hub import setup as prepare_setup


SOURCE = ROOT.parent / "source"


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
