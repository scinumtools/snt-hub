from __future__ import annotations

import re
from pathlib import Path

import pytest

from scinumtools3.dip import run_adapter_snapshot

from openfoam_dipl.generator import NATIVE_FIELDS, OpenFOAMAdapter, generate, load_environment
from openfoam_dipl.hub import setup


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "source"
SETUPS = ROOT / "setups.json"


def _control_values(text: str) -> dict[str, str]:
    return {key: value.strip() for key, value in re.findall(
        r"^\s*(startFrom|startTime|stopAt|endTime|deltaT|writeControl|writeInterval|"
        r"purgeWrite|writeFormat|writePrecision|writeCompression|timeFormat|timePrecision|"
        r"runTimeModifiable|adjustTimeStep|maxCo|maxAlphaCo|maxDeltaT)\s+([^;{}]+);",
        text, re.M,
    )}


def _scheme_value(text: str, section: str, key: str = "default") -> str | None:
    match = re.search(r"(?m)^" + re.escape(section) + r"\s*\n\s*\{([^}]*)\}", text, re.S)
    if not match:
        return None
    value = re.search(r"(?m)^\s*" + re.escape(key) + r"\s+([^;]+);", match.group(1))
    return value.group(1).strip() if value else None


def _dictionary_value(text: str, section: str | None, key: str) -> str | None:
    parts, current, quoted = [], [], False
    for char in section or "":
        if char == '"':
            quoted = not quoted
        if char == "." and not quoted:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    if current:
        parts.append("".join(current))
    for part in parts:
        if not part:
            continue
        match = re.search(r"(?m)^\s*" + re.escape(part) + r"\s*\n\s*\{", text)
        if not match:
            return None
        opening = text.find("{", match.start(), match.end())
        depth = 0
        closing = None
        for index in range(opening, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    closing = index
                    break
        if closing is None:
            return None
        text = text[opening + 1:closing]
    value = re.search(r"(?m)^\s*" + re.escape(key) + r"\s+([^;{}]+);", text)
    return value.group(1).strip() if value else None


def _equivalent(key: str, left: str, right: str) -> bool:
    if key in {"runTimeModifiable", "adjustTimeStep"}:
        left_bool = left.lower() in {"yes", "true", "on"}
        right_bool = right.lower() in {"yes", "true", "on"}
        return left_bool == right_bool
    try:
        return float(left) == pytest.approx(float(right))
    except ValueError:
        pass
    return left == right


@pytest.mark.parametrize("setup", sorted(__import__("json").loads(SETUPS.read_text())["setups"]))
def test_pinned_case_files_and_control_values_are_staged(setup: str, tmp_path: Path) -> None:
    output = generate(tmp_path / setup, setup)
    recipes = __import__("json").loads(SETUPS.read_text())["setups"]
    source_case = SOURCE / recipes[setup]["source_example"]
    original = (source_case / "system" / "controlDict").read_text()
    generated = (output / "system" / "controlDict").read_text()
    generated_values = _control_values(generated)
    original_values = _control_values(original)
    for _, (target, section, key) in NATIVE_FIELDS.items():
        if target == "system/controlDict" and key in original_values:
            assert _equivalent(key, generated_values[key], original_values[key])
    source_schemes = (source_case / "system" / "fvSchemes").read_text()
    generated_schemes = (output / "system" / "fvSchemes").read_text()
    for _, (target, section, key) in NATIVE_FIELDS.items():
        if target == "system/fvSchemes":
            source_value = _scheme_value(source_schemes, section, key)
            if source_value is not None:
                assert _scheme_value(generated_schemes, section, key) == source_value
    adapter = OpenFOAMAdapter(setup, SOURCE, ROOT / "dipl")
    environment = load_environment(setup)
    active_fields = adapter._available_fields(environment)
    mapped_targets = {"system/controlDict", "system/fvSchemes"}
    for _, (target, section, key) in active_fields.items():
        mapped_targets.add(target)
        if target not in {"system/controlDict", "system/fvSchemes"}:
            source_value = _dictionary_value((source_case / target).read_text(), section, key)
            generated_value = _dictionary_value((output / target).read_text(), section, key)
            assert source_value is not None and generated_value is not None
            assert _equivalent(key, generated_value, source_value)
    assert (output / "environment.diph5").is_file()
    for original_file in source_case.rglob("*"):
        if original_file.is_file() and original_file.relative_to(source_case).as_posix() not in mapped_targets:
            assert (output / original_file.relative_to(source_case)).read_bytes() == original_file.read_bytes()


def test_override_changes_native_control_dict(tmp_path: Path) -> None:
    override = tmp_path / "tune.dip"
    override.write_text('control.end_time = 0.75\noutput.write_precision = 12\n'
                        'discretization.gradient = "leastSquares"\n'
                        'fluid.kinematic_viscosity = 0.002 m2/s\n')
    output = generate(tmp_path / "cavity", "cavity_ico", override_file=override)
    values = _control_values((output / "system" / "controlDict").read_text())
    assert float(values["endTime"]) == pytest.approx(0.75)
    assert values["writePrecision"] == "12"
    assert _scheme_value((output / "system" / "fvSchemes").read_text(), "gradSchemes") == "leastSquares"
    transport = (output / "constant" / "transportProperties").read_text()
    assert float(_dictionary_value(transport, None, "nu")) == pytest.approx(0.002)


def test_solver_controls_override_native_fv_solution(tmp_path: Path) -> None:
    override = tmp_path / "solver.dip"
    override.write_text("pimple.correctors = 4\nalpha_solver.compression_coefficient = 0.75\n")
    output = generate(tmp_path / "dam", "dam_break_interfoam", override_file=override)
    solution = (output / "system" / "fvSolution").read_text()
    assert _dictionary_value(solution, "PIMPLE", "nCorrectors") == "4"
    assert _dictionary_value(solution, 'solvers."alpha.water.*"', "cAlpha") == "0.75"


def test_build_profile_is_generated_from_dipl_and_accepts_overrides(tmp_path: Path) -> None:
    default = generate(tmp_path / "default", "cavity_ico")
    profile = (default / "build-profile.sh").read_text()
    assert "WM_PRECISION_OPTION=DP" in profile
    assert "WM_LABEL_SIZE=32" in profile
    assert "WM_COMPILE_OPTION=Opt" in profile
    assert "WM_MPLIB=SYSTEMOPENMPI" in profile
    assert "WM_COMPILE_CONTROL='~openmp'" in profile
    assert "export WM_ARCH_OPTION=64" in profile

    override = tmp_path / "build.dip"
    override.write_text('build.precision = "SP"\nbuild.openmp = true\nbuild.label_bits = 64\n')
    changed = generate(tmp_path / "changed", "cavity_ico", override_file=override)
    changed_profile = (changed / "build-profile.sh").read_text()
    assert "WM_PRECISION_OPTION=SP" in changed_profile
    assert "WM_LABEL_SIZE=64" in changed_profile
    assert "WM_COMPILE_CONTROL='+openmp'" in changed_profile


def test_build_and_runtime_contracts_are_selectable_by_tag() -> None:
    env = load_environment("hot_room_boussinesq")
    build_nodes = {node.name for node in env.select("?", tags_all=["openfoam:config"])}
    runtime_nodes = {node.name for node in env.select("?", tags_all=["openfoam:param"])}
    assert build_nodes == {
        "build.compiler_type", "build.compiler", "build.precision", "build.label_bits",
        "build.compile_mode", "build.mpi", "build.openmp", "build.target_bits",
    }
    assert {"control.end_time", "fluid.kinematic_viscosity", "thermal_diffusivity"} <= runtime_nodes


def test_boussinesq_thermal_diffusivity_is_derived_from_fluid_controls() -> None:
    env = load_environment("hot_room_boussinesq")
    expected = env["fluid.kinematic_viscosity"].value / env["thermal.prandtl"].value
    assert env["thermal_diffusivity"].value == pytest.approx(expected)


def test_invalid_time_range_is_rejected(tmp_path: Path) -> None:
    override = tmp_path / "invalid.dip"
    override.write_text("control.start_time = 0.6\n")
    with pytest.raises(RuntimeError, match="does not satisfy its condition"):
        generate(tmp_path / "cavity", "cavity_ico", override_file=override)


def test_workspace_setup_records_source_and_override(tmp_path: Path) -> None:
    override = tmp_path / "tuning.dip"
    override.write_text("control.end_time = 0.75\n")
    output = setup("cavity_ico", tmp_path / "workspace-run", inputs_only=True,
                   override_file=override)
    assert (output / "system" / "controlDict").is_file()
    assert (output / "environment.diph5").is_file()
    assert (output / "input-overrides.dip").read_text() == override.read_text()
    lock = __import__("json").loads((output / "setup-lock.json").read_text())
    assert lock["source_revision"] == "481094fdf34f11ed6d0d603ee59a858a0124236d"
    assert lock["capability"] == "native-inputs-only"


def test_saved_output_plan_replays_case_and_native_controls(tmp_path: Path) -> None:
    first = generate(tmp_path / "first", "dam_break_interfoam")
    replay = tmp_path / "replay"
    adapter = OpenFOAMAdapter("dam_break_interfoam", SOURCE, ROOT / "dipl")
    run_adapter_snapshot(first / "environment.diph5", adapter, replay)
    assert (first / "system" / "controlDict").read_bytes() == (replay / "system" / "controlDict").read_bytes()
    assert (first / "system" / "fvSchemes").read_bytes() == (replay / "system" / "fvSchemes").read_bytes()
    assert (first / "constant" / "transportProperties").read_bytes() == (replay / "constant" / "transportProperties").read_bytes()
    assert (first / "system" / "fvSolution").read_bytes() == (replay / "system" / "fvSolution").read_bytes()
    assert (first / "build-profile.sh").read_bytes() == (replay / "build-profile.sh").read_bytes()
    assert (first / "0.orig" / "U").read_bytes() == (replay / "0.orig" / "U").read_bytes()
