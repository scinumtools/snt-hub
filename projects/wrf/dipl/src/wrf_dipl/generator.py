"""Patch reviewed WRF namelists from DIPL and stage their pinned text inputs."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from scinumtools3.dip import Adapter, ExistingOutputPolicy, inspect_table, run_adapter
from snt_hub_runtime.dipl import evaluate_project
from snt_hub_runtime.output_plan import PlannedValues


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
PARAMETER_TAG = "wrf:param"
SOUNDING_VALUE_TAG = "wrf:sounding-value"
SOUNDING_OUTPUT_TAG = "wrf:sounding-output"
NATIVE_SECTIONS = {"time_control", "domains", "dynamics", "bdy_control", "ideal"}
SOUNDING_COLUMNS = (
    "height", "potential_temperature", "water_vapor_mixing_ratio", "u_wind", "v_wind",
)
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


def _format_sounding_value(value: Any) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise GenerationError(f"Unsupported WRF sounding value: {value!r}")
    return f"{float(value):.9g}"


def render_input_sounding(env: Any, outputs: Any) -> str:
    """Render the tagged surface values and typed profile table in WRF's native layout."""
    values = PlannedValues(outputs)
    surface_paths = (
        "sounding.surface.pressure",
        "sounding.surface.potential_temperature",
        "sounding.surface.water_vapor_mixing_ratio",
    )
    surface = [_format_sounding_value(_value(values, path)) for path in surface_paths]

    table = inspect_table(env, "sounding.profile")
    columns = {column.path.rsplit(".", 1)[-1]: list(_value(env, column.path))
               for column in table.columns}
    if set(columns) != set(SOUNDING_COLUMNS):
        raise GenerationError(f"WRF sounding table needs columns {SOUNDING_COLUMNS}")
    lengths = {len(columns[name]) for name in SOUNDING_COLUMNS}
    if len(lengths) != 1 or not lengths or next(iter(lengths)) == 0:
        raise GenerationError("WRF sounding profile columns must have equal, nonzero lengths")

    lines = [" ".join(surface)]
    for row in zip(*(columns[name] for name in SOUNDING_COLUMNS)):
        lines.append(" ".join(_format_sounding_value(value) for value in row))
    return "\n".join(lines) + "\n"


def _sounding_output_path(outputs: Any) -> str:
    mappings = outputs.select("sounding:file", True)
    if len(mappings) != 1 or mappings[0].key != "input_sounding":
        raise GenerationError("The WRF sounding adapter needs one input_sounding output mapping")
    path = Path(mappings[0].value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != "input_sounding":
        raise GenerationError("The generated WRF sounding path must be input_sounding")
    return path.as_posix()


def _native_fields(env: Any, setup: str) -> dict[str, tuple[str, ...]]:
    """Discover WRF namelist fields from tagged DIPL nodes and their native paths."""
    fields: dict[str, list[str]] = {}
    seen: set[str] = set()
    for node in env.select("?", tags_all=[PARAMETER_TAG]):
        native = list(node.metadata.native)
        if len(native) != 1:
            raise GenerationError(f"Tagged parameter `{node.name}` needs one ?native path")
        section, separator, key = native[0].partition(".")
        if not separator or section not in NATIVE_SECTIONS or not key:
            raise GenerationError(f"Unsupported WRF native path `{native[0]}` on `{node.name}`")
        if node.name != native[0]:
            raise GenerationError(f"WRF DIPL path `{node.name}` must match ?native `{native[0]}`")
        if native[0] in seen:
            raise GenerationError(f"Repeated WRF native path `{native[0]}`")
        seen.add(native[0])
        fields.setdefault(section, []).append(key)

    required = {"time_control", "domains", "dynamics", "bdy_control"}
    if UPSTREAM_CASES[setup][2] is not None:
        required.add("ideal")
    missing = sorted(required - fields.keys())
    if missing:
        raise GenerationError(f"WRF DIPL contract is missing tagged sections: {missing}")
    return {section: tuple(keys) for section, keys in fields.items()}


def render_namelist(env: Any, original: str, setup: str,
                    fields: dict[str, tuple[str, ...]] | None = None) -> str:
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

    if fields is None:
        fields = _native_fields(env, setup)

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
        self.assets = tuple(asset for asset in UPSTREAM_CASES[setup][1]
                            if not (setup == "hill_2d" and asset == "input_sounding"))

    def describe_outputs(self, env: Any, outputs: Any) -> None:
        fields = _native_fields(env, self.setup)
        for section, keys in fields.items():
            for key in keys:
                path = f"{section}.{key}"
                outputs.add_node(env, path, f"namelist:{section}", key, path,
                                 rule="modeled WRF namelist field", origin="adapter:wrf")
        if self.setup == "hill_2d":
            for node in env.select("?", tags_all=[SOUNDING_VALUE_TAG]):
                outputs.add_node(env, f"sounding:{node.name}", "sounding:surface", node.name,
                                 node.name, rule="WRF input sounding surface value",
                                 origin="adapter:wrf")
            output_nodes = env.select("?", tags_all=[SOUNDING_OUTPUT_TAG])
            if len(output_nodes) != 1:
                raise GenerationError("hill_2d needs one tagged WRF sounding output filename")
            outputs.add_node(env, "sounding:file", "sounding:file", "input_sounding",
                             output_nodes[0].name, rule="WRF input sounding profile",
                             origin="adapter:wrf")

    def plan_resolved(self, env: Any, outputs: Any, context: Any) -> None:
        namelist = self.case_dir / "namelist.input"
        if not namelist.is_file() or any(not (self.case_dir / asset).is_file() for asset in self.assets):
            raise GenerationError(f"Pinned WRF example files are missing in {self.case_dir}")
        fields = _native_fields(env, self.setup)
        context.add_text("namelist.input", render_namelist(
            PlannedValues(outputs), namelist.read_text(), self.setup, fields))
        if self.setup == "hill_2d":
            context.add_text(_sounding_output_path(outputs), render_input_sounding(env, outputs))
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
