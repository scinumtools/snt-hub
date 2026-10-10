"""Patch reviewed WRF namelists from DIPL and stage their pinned text inputs."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from scinumtools3.dip import Adapter, ExistingOutputPolicy, run_adapter
from snt_hub_runtime.dipl import evaluate_project


ROOT = Path(__file__).resolve().parents[2]
UPSTREAM_CASES = {
    "hill_2d": ("em_hill2d_x", ("input_sounding",), 1),
    "gravity_current_2d": ("em_grav2d_x", ("input_sounding",), 6),
    "baroclinic_wave": ("em_b_wave", ("input_jet",), 7),
    "convective_radiative": ("em_convrad", ("input_sounding",), 3),
    "held_suarez": ("em_heldsuarez", (), None),
    "quarter_supercell": ("em_quarter_ss", ("input_sounding",), 2),
    "sea_breeze_2d": ("em_seabreeze2d_x", ("input_sounding",), None),
    "squall_line_x": ("em_squall2d_x", ("input_sounding",), 4),
    "squall_line_y": ("em_squall2d_y", ("input_sounding",), 5),
    "tropical_cyclone": ("em_tropical_cyclone", ("input_sounding",), None),
}
X_2D_CASES = {"hill_2d", "gravity_current_2d", "sea_breeze_2d", "squall_line_x"}
Y_2D_CASES = {"squall_line_y"}
FIELDS = {
    "time_control": ("run_days", "run_hours", "run_minutes", "history_interval"),
    "domains": ("time_step", "e_we", "e_sn", "e_vert", "dx", "dy", "ztop"),
    "dynamics": ("hybrid_opt", "damp_opt", "zdamp", "dampcoef", "khdif", "kvdif"),
    "bdy_control": ("periodic_x", "open_xs", "open_xe"),
    "ideal": ("ideal_case",),
}
SECTION = re.compile(r"^\s*&([a-z_]+)\s*$", re.I)
ASSIGNMENT = re.compile(r"^(\s*)([a-z_]+)(\s*=\s*)([^!,\n]+)(,?)(.*)$", re.I)


class GenerationError(ValueError):
    pass


def load_environment(setup: str, bundle_root: Path = ROOT,
                     override_file: Path | None = None) -> Any:
    if setup not in UPSTREAM_CASES:
        raise GenerationError(f"Unknown WRF setup: {setup}")
    manifest = Path(bundle_root) / "examples" / setup / "DIPfile"
    return evaluate_project(manifest, override_file)


def _value(env: Any, path: str) -> Any:
    return env[path].value


def _native_value(raw: str) -> int | float | bool:
    token = raw.strip().lower()
    if token in (".true.", ".false."):
        return token == ".true."
    if re.fullmatch(r"[+-]?\d+", token):
        return int(token)
    return float(token.replace("d", "e"))


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return ".true." if value else ".false."
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.12g}"
    raise GenerationError(f"Unsupported WRF namelist value: {value!r}")


def render_namelist(env: Any, original: str, setup: str) -> str:
    """Preserve all pinned entries; replace only modeled values that changed."""
    if setup not in UPSTREAM_CASES:
        raise GenerationError(f"Unknown WRF setup: {setup}")
    e_we, e_sn = _value(env, "domains.e_we"), _value(env, "domains.e_sn")
    if e_we < 3 or e_sn < 3 or (e_we == 3 and e_sn == 3):
        raise GenerationError("WRF horizontal grid must have at least one resolved direction")
    if setup in X_2D_CASES and e_sn != 3:
        raise GenerationError("This x-oriented WRF initializer requires e_sn = 3")
    if setup in Y_2D_CASES and e_we != 3:
        raise GenerationError("This y-oriented WRF initializer requires e_we = 3")
    if setup not in X_2D_CASES | Y_2D_CASES and (e_we == 3 or e_sn == 3):
        raise GenerationError("This 3D WRF initializer requires both horizontal directions")
    if _value(env, "domains.e_vert") <= 2:
        raise GenerationError("WRF grid dimensions must exceed the idealized boundary cells")
    if _value(env, "domains.ztop") <= 0:
        raise GenerationError("WRF model top must be positive")
    if (_value(env, "bdy_control.periodic_x") and
            (_value(env, "bdy_control.open_xs") or _value(env, "bdy_control.open_xe"))):
        raise GenerationError("Periodic x boundaries cannot also be open")
    ideal_case = UPSTREAM_CASES[setup][2]
    if ideal_case is not None and _value(env, "ideal.ideal_case") != ideal_case:
        raise GenerationError("The ideal case must match the pinned WRF initializer and sounding")

    fields = {section: keys for section, keys in FIELDS.items()
              if section != "ideal" or ideal_case is not None}

    section = None
    seen: set[tuple[str, str]] = set()
    lines = []
    for line in original.splitlines(keepends=True):
        match = SECTION.match(line.rstrip("\n"))
        if match:
            section = match.group(1).lower()
        elif line.strip() == "/":
            section = None
        assignment = ASSIGNMENT.match(line.rstrip("\n")) if section in fields else None
        if assignment and assignment.group(2).lower() in fields[section]:
            key = assignment.group(2).lower()
            path = f"{section}.{key}"
            desired = _value(env, path)
            original_value = _native_value(assignment.group(4))
            seen.add((section, key))
            if desired != original_value:
                line = (assignment.group(1) + assignment.group(2) + assignment.group(3) +
                        _format_value(desired) + assignment.group(5) + assignment.group(6) +
                        ("\n" if line.endswith("\n") else ""))
        lines.append(line)
    required = {(section, key) for section, keys in fields.items() for key in keys}
    if seen != required:
        raise GenerationError(f"Pinned WRF namelist is missing modeled fields: {sorted(required - seen)}")
    return "".join(lines)


class WrfAdapter(Adapter):
    def __init__(self, setup: str, source_root: Path):
        super().__init__()
        self.setup = setup
        self.case_dir = source_root / "test" / UPSTREAM_CASES[setup][0]
        self.assets = UPSTREAM_CASES[setup][1]

    def plan(self, env: Any, context: Any) -> None:
        namelist = self.case_dir / "namelist.input"
        if not namelist.is_file() or any(not (self.case_dir / asset).is_file() for asset in self.assets):
            raise GenerationError(f"Pinned WRF example files are missing in {self.case_dir}")
        context.add_text("namelist.input", render_namelist(env, namelist.read_text(), self.setup))
        for asset in self.assets:
            context.add_binary(asset, (self.case_dir / asset).read_bytes())


def generate(output: Path, setup: str = "hill_2d", bundle_root: Path = ROOT,
             override_file: Path | None = None, source_root: Path | None = None) -> Path:
    bundle_root = Path(bundle_root).resolve()
    source = Path(source_root).resolve() if source_root else bundle_root.parent / "source"
    env = load_environment(setup, bundle_root, override_file)
    run_adapter(env, WrfAdapter(setup, source), output, "environment.diph5",
                existing_output_policy=ExistingOutputPolicy.ReplaceRegistered)
    return Path(output)
