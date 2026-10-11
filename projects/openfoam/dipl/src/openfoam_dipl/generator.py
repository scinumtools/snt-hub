"""Stage pinned OpenFOAM tutorial files and render selected DIPL controls."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from scinumtools3.dip import Adapter, ExistingOutputPolicy, run_adapter
from snt_hub_runtime.dipl import evaluate_project
from snt_hub_runtime.output_plan import PlannedValues


ROOT = Path(__file__).resolve().parents[2]
NATIVE_FIELDS = {
    "control.start_from": ("system/controlDict", None, "startFrom"),
    "control.start_time": ("system/controlDict", None, "startTime"),
    "control.stop_at": ("system/controlDict", None, "stopAt"),
    "control.end_time": ("system/controlDict", None, "endTime"),
    "control.delta_t": ("system/controlDict", None, "deltaT"),
    "control.write_control": ("system/controlDict", None, "writeControl"),
    "control.write_interval": ("system/controlDict", None, "writeInterval"),
    "output.purge_write": ("system/controlDict", None, "purgeWrite"),
    "output.write_format": ("system/controlDict", None, "writeFormat"),
    "output.write_precision": ("system/controlDict", None, "writePrecision"),
    "output.write_compression": ("system/controlDict", None, "writeCompression"),
    "output.time_format": ("system/controlDict", None, "timeFormat"),
    "output.time_precision": ("system/controlDict", None, "timePrecision"),
    "output.run_time_modifiable": ("system/controlDict", None, "runTimeModifiable"),
    "adaptive.adjust_time_step": ("system/controlDict", None, "adjustTimeStep"),
    "adaptive.max_co": ("system/controlDict", None, "maxCo"),
    "adaptive_limits.max_delta_t": ("system/controlDict", None, "maxDeltaT"),
    "phase_time.max_alpha_co": ("system/controlDict", None, "maxAlphaCo"),
    "discretization.time_derivative": ("system/fvSchemes", "ddtSchemes", "default"),
    "discretization.gradient": ("system/fvSchemes", "gradSchemes", "default"),
    "discretization.laplacian": ("system/fvSchemes", "laplacianSchemes", "default"),
    "discretization.interpolation": ("system/fvSchemes", "interpolationSchemes", "default"),
    "discretization.surface_normal_gradient": ("system/fvSchemes", "snGradSchemes", "default"),
    "divergence.default": ("system/fvSchemes", "divSchemes", "default"),
    "divergence.density_velocity": ("system/fvSchemes", "divSchemes", "div(rhoPhi,U)"),
    "divergence.phase_fraction": ("system/fvSchemes", "divSchemes", "div(phi,alpha)"),
    "divergence.phase_compression": ("system/fvSchemes", "divSchemes", "div(phirb,alpha)"),
    "viscous_divergence.viscous_stress": ("system/fvSchemes", "divSchemes", "div(((rho*nuEff)*dev2(T(grad(U)))))"),
    "fluid.kinematic_viscosity": ("constant/transportProperties", None, "nu"),
    "water.transport_model": ("constant/transportProperties", "water", "transportModel"),
    "water.kinematic_viscosity": ("constant/transportProperties", "water", "nu"),
    "water.density": ("constant/transportProperties", "water", "rho"),
    "air.transport_model": ("constant/transportProperties", "air", "transportModel"),
    "air.kinematic_viscosity": ("constant/transportProperties", "air", "nu"),
    "air.density": ("constant/transportProperties", "air", "rho"),
    "surface.surface_tension": ("constant/transportProperties", None, "sigma"),
    "thermal.thermal_expansion": ("constant/transportProperties", None, "beta"),
    "thermal.reference_temperature": ("constant/transportProperties", None, "TRef"),
    "thermal.prandtl": ("constant/transportProperties", None, "Pr"),
    "thermal.turbulent_prandtl": ("constant/transportProperties", None, "Prt"),
    "mhd_fluid.density": ("constant/transportProperties", None, "rho"),
    "mhd_fluid.kinematic_viscosity": ("constant/transportProperties", None, "nu"),
    "mhd_fluid.dynamic_viscosity": ("constant/transportProperties", None, "mu"),
    "mhd_fluid.electrical_conductivity": ("constant/transportProperties", None, "sigma"),
    "mechanical_material.density": ("constant/mechanicalProperties", "rho", "value"),
    "mechanical_material.poisson_ratio": ("constant/mechanicalProperties", "nu", "value"),
    "mechanical_material.young_modulus": ("constant/mechanicalProperties", "E", "value"),
    "mechanical_material.plane_stress": ("constant/mechanicalProperties", None, "planeStress"),
    "thermal_material.specific_heat": ("constant/thermalProperties", "C", "value"),
    "thermal_material.thermal_conductivity": ("constant/thermalProperties", "k", "value"),
    "thermal_material.thermal_diffusivity": ("constant/thermalProperties", "alpha", "value"),
    "thermal_material.thermal_stress": ("constant/thermalProperties", None, "thermalStress"),
    "gas.molecular_weight": ("constant/thermophysicalProperties", "mixture.specie", "molWeight"),
    "gas.specific_heat": ("constant/thermophysicalProperties", "mixture.thermodynamics", "Cp"),
    "gas.formation_enthalpy": ("constant/thermophysicalProperties", "mixture.thermodynamics", "Hf"),
    "gas.dynamic_viscosity": ("constant/thermophysicalProperties", "mixture.transport", "mu"),
    "gas.prandtl": ("constant/thermophysicalProperties", "mixture.transport", "Pr"),
    "piso.correctors": ("system/fvSolution", "PISO", "nCorrectors"),
    "piso.non_orthogonal_correctors": ("system/fvSolution", "PISO", "nNonOrthogonalCorrectors"),
    "bpiso.correctors": ("system/fvSolution", "BPISO", "nCorrectors"),
    "pimple.outer_correctors": ("system/fvSolution", "PIMPLE", "nOuterCorrectors"),
    "pimple.correctors": ("system/fvSolution", "PIMPLE", "nCorrectors"),
    "pimple.non_orthogonal_correctors": ("system/fvSolution", "PIMPLE", "nNonOrthogonalCorrectors"),
    "simple.non_orthogonal_correctors": ("system/fvSolution", "SIMPLE", "nNonOrthogonalCorrectors"),
    "solid_solver.correctors": ("system/fvSolution", "stressAnalysis", "nCorrectors"),
    "alpha_solver.corrections": ("system/fvSolution", 'solvers."alpha.water.*"', "nAlphaCorr"),
    "alpha_solver.subcycles": ("system/fvSolution", 'solvers."alpha.water.*"', "nAlphaSubCycles"),
    "alpha_solver.compression_coefficient": ("system/fvSolution", 'solvers."alpha.water.*"', "cAlpha"),
    "alpha_solver.limiter_iterations": ("system/fvSolution", 'solvers."alpha.water.*"', "nLimiterIter"),
    "alpha_solver.multi_correction": ("system/fvSolution", 'solvers."alpha.water.*"', "MULESCorr"),
    "alpha_solver.tolerance": ("system/fvSolution", 'solvers."alpha.water.*"', "tolerance"),
    "alpha_solver.relative_tolerance": ("system/fvSolution", 'solvers."alpha.water.*"', "relTol"),
    "pressure_solver.tolerance": ("system/fvSolution", "solvers.p", "tolerance"),
    "pressure_solver.relative_tolerance": ("system/fvSolution", "solvers.p", "relTol"),
    "velocity_solver.tolerance": ("system/fvSolution", "solvers.U", "tolerance"),
    "velocity_solver.relative_tolerance": ("system/fvSolution", "solvers.U", "relTol"),
    "flow_solver.tolerance": ("system/fvSolution", 'solvers."(U|k|epsilon|omega|f|v2)"', "tolerance"),
    "flow_solver.relative_tolerance": ("system/fvSolution", 'solvers."(U|k|epsilon|omega|f|v2)"', "relTol"),
    "solid_field_solver.tolerance": ("system/fvSolution", 'solvers."(D|T)"', "tolerance"),
    "solid_field_solver.relative_tolerance": ("system/fvSolution", 'solvers."(D|T)"', "relTol"),
    "mesh_solver.tolerance": ("system/fvSolution", "solvers.cellDisplacement", "tolerance"),
    "mesh_solver.relative_tolerance": ("system/fvSolution", "solvers.cellDisplacement", "relTol"),
}
SETUP_NATIVE_FIELD_OVERRIDES = {
    "dam_break_interfoam": {
        "pressure_solver.tolerance": ("system/fvSolution", "solvers.p_rgh", "tolerance"),
        "pressure_solver.relative_tolerance": ("system/fvSolution", "solvers.p_rgh", "relTol"),
    },
    "hot_room_boussinesq": {
        "pressure_solver.tolerance": ("system/fvSolution", "solvers.p_rgh", "tolerance"),
        "pressure_solver.relative_tolerance": ("system/fvSolution", "solvers.p_rgh", "relTol"),
    },
    "pitz_daily_simple": {
        "flow_solver.tolerance": ("system/fvSolution", 'solvers."(U|k|epsilon|omega|f|v2)"', "tolerance"),
        "flow_solver.relative_tolerance": ("system/fvSolution", 'solvers."(U|k|epsilon|omega|f|v2)"', "relTol"),
    },
    "rotating_square_dynamic": {
        "flow_solver.tolerance": ("system/fvSolution", 'solvers."(U|k|epsilon)"', "tolerance"),
        "flow_solver.relative_tolerance": ("system/fvSolution", 'solvers."(U|k|epsilon)"', "relTol"),
    },
    "hot_room_boussinesq": {
        "flow_solver.tolerance": ("system/fvSolution", 'solvers."(U|T|k|epsilon|R)"', "tolerance"),
        "flow_solver.relative_tolerance": ("system/fvSolution", 'solvers."(U|T|k|epsilon|R)"', "relTol"),
    },
    "counterflow_flame": {
        "flow_solver.tolerance": ("system/fvSolution", 'solvers."(U|h|k|epsilon)"', "tolerance"),
        "flow_solver.relative_tolerance": ("system/fvSolution", 'solvers."(U|h|k|epsilon)"', "relTol"),
    },
    "hartmann_mhd": {
        "flow_solver.tolerance": ("system/fvSolution", 'solvers."(U|B)"', "tolerance"),
        "flow_solver.relative_tolerance": ("system/fvSolution", 'solvers."(U|B)"', "relTol"),
    },
}
BUILD_PROFILE_ORDER = (
    "WM_ARCH_OPTION", "WM_COMPILER_TYPE", "WM_COMPILER", "WM_PRECISION_OPTION",
    "WM_LABEL_SIZE", "WM_COMPILE_OPTION", "WM_MPLIB", "WM_COMPILE_CONTROL",
)
SCHEME_FIELDS = {path: spec for path, spec in NATIVE_FIELDS.items()
                 if spec[0] == "system/fvSchemes"}
ASSIGNMENT = re.compile(r"^(\s*)([A-Za-z][A-Za-z0-9]*)(\s+)([^;]+)(;.*)$")


class GenerationError(ValueError):
    pass


def _recipes(bundle_root: Path) -> dict[str, dict]:
    import json

    return json.loads((Path(bundle_root).resolve().parent / "setups.json").read_text())["setups"]


def load_environment(setup: str, bundle_root: Path = ROOT,
                     override_file: Path | None = None) -> Any:
    manifest = Path(bundle_root) / "examples" / setup / "DIPfile"
    if not manifest.is_file():
        raise GenerationError(f"Unknown OpenFOAM setup: {setup}")
    return evaluate_project(manifest, override_file)


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return f"{value:.12g}" if isinstance(value, float) else str(value)
    if isinstance(value, str) and not any(char in value for char in "\n\r;{}"):
        return value
    raise GenerationError(f"Unsupported OpenFOAM control value: {value!r}")


def _replace_top_level(text: str, key: str, value: str) -> tuple[str, int]:
    lines = []
    count = 0
    for line in text.splitlines(keepends=True):
        ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
        match = ASSIGNMENT.match(line.rstrip("\r\n"))
        if match and match.group(2) == key:
            line = match.group(1) + key + match.group(3) + value + match.group(5) + ending
            count += 1
        lines.append(line)
    return "".join(lines), count


def _section_bounds(text: str, section: str) -> tuple[int, int]:
    start, end = 0, len(text)
    for part in _section_parts(section):
        match = re.search(r"(?m)^[ \t]*" + re.escape(part) + r"[ \t]*\n[ \t]*\{", text[start:end])
        if not match:
            raise GenerationError(f"OpenFOAM dictionary is missing section {section}")
        match_start = start + match.start()
        opening = text.find("{", match_start, start + match.end())
        start, end = opening + 1, _block_end(text, opening, section)
    return start - 1, end


def _section_parts(section: str) -> list[str]:
    """Split nested dictionary paths while preserving dots inside quoted keys."""
    parts, current, quoted = [], [], False
    for char in section:
        if char == '"':
            quoted = not quoted
        if char == "." and not quoted:
            parts.append("".join(current))
            current = []
        else:
            current.append(char)
    if current:
        parts.append("".join(current))
    return parts


def _block_end(text: str, opening: int, section: str) -> int:
    depth, i, quoted, line_comment, block_comment = 0, opening, False, False, False
    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if line_comment:
            if char == "\n": line_comment = False
        elif block_comment:
            if char == "*" and nxt == "/": block_comment = False; i += 1
        elif quoted:
            if char == "\\": i += 1
            elif char == '"': quoted = False
        elif char == "/" and nxt == "/": line_comment = True; i += 1
        elif char == "/" and nxt == "*": block_comment = True; i += 1
        elif char == '"': quoted = True
        elif char == "{": depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0: return i
        i += 1
    raise GenerationError(f"Unclosed OpenFOAM dictionary section {section}")


def _replace_section_entry(text: str, section: str, key: str, value: str) -> tuple[str, int]:
    opening, closing = _section_bounds(text, section)
    body = text[opening + 1:closing]
    pattern = re.compile(r"(?m)^(\s*)" + re.escape(key) + r"(\s+)([^;]+)(;.*)$")
    matches = list(pattern.finditer(body))
    if len(matches) != 1:
        raise GenerationError(f"Expected one {section}.{key} entry, found {len(matches)}")
    match = matches[0]
    replacement = match.group(1) + key + match.group(2) + value + match.group(4)
    updated = body[:match.start()] + replacement + body[match.end():]
    return text[:opening + 1] + updated + text[closing:], 1


def render_native_file(env: Any, relative: str, original: str,
                       native_fields: dict[str, tuple[str, str | None, str]]) -> str:
    """Render modeled scalar entries while preserving the tutorial's other text."""
    lines = []
    result = original
    expected = {path: spec for path, spec in native_fields.items() if spec[0] == relative}
    for path, (_, section, key) in expected.items():
        if section is None:
            result, count = _replace_top_level(result, key, _format_value(env[path].value))
        else:
            result, count = _replace_section_entry(result, section, key, _format_value(env[path].value))
        if count != 1:
            location = f"{section}.{key}" if section else key
            raise GenerationError(f"Expected one {location} entry in {relative}, found {count}")
    return result


def render_build_profile(env: Any, fields: dict[str, str]) -> str:
    """Render the DIPL build choices as a sourceable v2606 environment profile."""
    values = {path: env[path].value for path in fields}
    openmp = "+openmp" if values["build.openmp"] else "~openmp"
    variables = {
        native: openmp if path == "build.openmp" else _format_value(values[path])
        for path, native in fields.items()
    }
    lines = [
        "#!/usr/bin/env bash",
        "# Generated from the build.* nodes in this DIPL setup.",
        "# Set OPENFOAM_SOURCE to the pinned OpenFOAM v2606 source checkout.",
        ': "${OPENFOAM_SOURCE:?Set OPENFOAM_SOURCE to the OpenFOAM v2606 source checkout}"',
        f"export WM_ARCH_OPTION={variables['WM_ARCH_OPTION']}",
        f"export WM_COMPILE_CONTROL={variables['WM_COMPILE_CONTROL']!r}",
        '. "$OPENFOAM_SOURCE/etc/bashrc" \\',
    ]
    args = [f"{native}={variables[native]}" for native in fields.values()
            if native not in {"WM_COMPILE_CONTROL", "WM_ARCH_OPTION"}]
    lines.extend(f"  {arg} \\" for arg in args[:-1])
    lines.append(f"  {args[-1]}")
    lines.extend([
        "",
        "# Then build from the source checkout, for example:",
        '# (cd "$OPENFOAM_SOURCE" && ./Allwmake -j)',
        "",
    ])
    return "\n".join(lines)


def _build_profile_fields(env: Any) -> dict[str, str]:
    """Resolve the complete, uniquely mapped build contract from DIPL tags."""
    by_native: dict[str, str] = {}
    for node in env.select("?", tags_all=["openfoam:config"]):
        native = list(node.metadata.native)
        if len(native) != 1:
            raise GenerationError(f"Build setting `{node.name}` needs one ?native name")
        variable = native[0]
        if variable not in BUILD_PROFILE_ORDER or variable in by_native:
            raise GenerationError(f"Unsupported or repeated OpenFOAM build setting `{variable}`")
        by_native[variable] = node.name
    missing = sorted(set(BUILD_PROFILE_ORDER) - set(by_native))
    if missing:
        raise GenerationError(f"Build configuration is missing tagged settings: {missing}")
    return {by_native[variable]: variable for variable in BUILD_PROFILE_ORDER}


def _entry_exists(text: str, section: str | None, key: str) -> bool:
    if section is None:
        return len(re.findall(r"(?m)^\s*" + re.escape(key) + r"\s+[^;{}]+;", text)) == 1
    try:
        opening, closing = _section_bounds(text, section)
    except GenerationError:
        return False
    body = text[opening + 1:closing]
    return len(re.findall(r"(?m)^\s*" + re.escape(key) + r"\s+[^;{}]+;", body)) == 1


class OpenFOAMAdapter(Adapter):
    def __init__(self, setup: str, source_root: Path, bundle_root: Path):
        super().__init__()
        recipes = _recipes(bundle_root)
        if setup not in recipes:
            raise GenerationError(f"Unknown OpenFOAM setup: {setup}")
        self.setup = setup
        self.case_dir = (Path(source_root).resolve() / recipes[setup]["source_example"]).resolve()
        self.source_root = Path(source_root).resolve()
        if not self.case_dir.is_relative_to(self.source_root) or not self.case_dir.is_dir():
            raise GenerationError(f"Pinned tutorial case is missing or escapes source: {self.case_dir}")
        self.native_fields = {}
        native_fields = dict(NATIVE_FIELDS)
        native_fields.update(SETUP_NATIVE_FIELD_OVERRIDES.get(setup, {}))
        for path, spec in native_fields.items():
            relative, section, key = spec
            native_file = self.case_dir / relative
            if native_file.is_file() and _entry_exists(native_file.read_text(), section, key):
                self.native_fields[path] = spec
        self.active_fields = {}
        self.active_build_fields = {}

    def _available_fields(self, env: Any) -> dict[str, tuple[str, str | None, str]]:
        tagged_paths = {
            node.name for node in env.select("?", tags_all=["openfoam:param"])
        }
        available = {}
        for path, spec in self.native_fields.items():
            if path not in tagged_paths:
                continue
            try:
                env[path]
            except Exception:
                continue
            available[path] = spec
        return available

    def describe_outputs(self, env: Any, outputs: Any) -> None:
        self.active_fields = self._available_fields(env)
        for path, (target, section, key) in self.active_fields.items():
            native_key = f"{section}.{key}" if section else key
            outputs.add_node(env, path, f"file:{target}", native_key, path,
                             rule="modeled OpenFOAM input setting",
                             origin="adapter:openfoam")
        self.active_build_fields = _build_profile_fields(env)
        for path, variable in self.active_build_fields.items():
            outputs.add_node(env, path, "file:build-profile.sh", variable, path,
                             rule="OpenFOAM v2606 build environment setting",
                             origin="adapter:openfoam")

    def plan_resolved(self, env: Any, outputs: Any, context: Any) -> None:
        self.active_fields = self._available_fields(env)
        self.active_build_fields = _build_profile_fields(env)
        planned = PlannedValues(outputs)
        for path in sorted(self.case_dir.rglob("*")):
            if path.is_symlink():
                raise GenerationError(f"Symlinked tutorial assets are not supported: {path}")
            if not path.is_file():
                continue
            relative = path.relative_to(self.case_dir).as_posix()
            if relative in {spec[0] for spec in self.active_fields.values()}:
                text = render_native_file(planned, relative, path.read_text(), self.active_fields)
                context.add_text(relative, text)
            else:
                context.add_binary(relative, path.read_bytes())
        context.add_text("build-profile.sh",
                         render_build_profile(planned, self.active_build_fields))


def generate(output: Path, setup: str = "cavity_ico", bundle_root: Path = ROOT,
             override_file: Path | None = None, source_root: Path | None = None) -> Path:
    bundle = Path(bundle_root).resolve()
    source = Path(source_root).resolve() if source_root else bundle.parent / "source"
    env = load_environment(setup, bundle, override_file)
    adapter = OpenFOAMAdapter(setup, source, bundle)
    run_adapter(env, adapter, output, "environment.diph5",
                existing_output_policy=ExistingOutputPolicy.ReplaceRegistered)
    return Path(output)
