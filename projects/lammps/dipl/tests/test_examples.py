from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import shlex

import pytest

from lammps_dipl.generator import ROOT, load_environment, render_lammps
from lammps_dipl.hub import setup as prepare_setup


SOURCE = ROOT.parent / "source"
REFERENCES = {
    "lj_melt": SOURCE / "examples" / "melt" / "in.melt",
    "lj_minimize_2d": SOURCE / "examples" / "min" / "in.min",
}


def commands(text: str) -> list[tuple]:
    parsed = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        tokens = shlex.split(line, comments=True)
        if not tokens:
            continue
        if tokens[0] == "neigh_modify":
            args = dict(zip(tokens[1::2], tokens[2::2]))
            tokens = ["neigh_modify", *[f"{key}={args[key]}" for key in sorted(args)]]
        normalized = []
        for token in tokens:
            if "=" in token:
                key, value = token.split("=", 1)
                normalized.append((key, value))
                continue
            try:
                normalized.append(Decimal(token))
            except InvalidOperation:
                normalized.append(token)
        parsed.append(tuple(normalized))
    return parsed


@pytest.mark.parametrize("setup", sorted(REFERENCES))
def test_active_commands_match_pinned_example(setup):
    generated = render_lammps(load_environment(setup))
    assert commands(generated) == commands(REFERENCES[setup].read_text())


def test_invalid_box_override_is_rejected(tmp_path):
    override = tmp_path / "invalid.dip"
    override.write_text("geometry.xhi = -1\n")
    with pytest.raises(ValueError, match="box bounds"):
        render_lammps(load_environment("lj_melt", override_file=override))


@pytest.mark.parametrize("setup", sorted(REFERENCES))
def test_complete_setup_records_pinned_source_and_native_input(setup, tmp_path):
    output = tmp_path / setup
    prepare_setup(setup, output)
    lock = json.loads((output / "setup-lock.json").read_text())
    assert lock["capability"] == "complete"
    assert lock["source_revision"] == "8de817dd79bfe4525d5d39246a212d833e6dee07"
    assert "in.lammps" in lock["files"]
    assert (output / "environment.diph5").is_file()
    with pytest.raises(RuntimeError, match="already exists"):
        prepare_setup(setup, output)


def test_override_changes_generated_run_and_records_digest(tmp_path):
    override = tmp_path / "short-run.dip"
    override.write_text("dynamics.run_steps = 5\n")
    output = tmp_path / "run"
    prepare_setup("lj_melt", output, override_file=override)
    assert "run 5\n" in (output / "in.lammps").read_text()
    assert (output / "input-overrides.dip").read_text() == override.read_text()
    assert json.loads((output / "setup-lock.json").read_text())["inputs"]["override_sha256"]
