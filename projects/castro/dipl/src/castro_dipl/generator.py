"""Render the pinned Castro Sedov input with selected DIPL controls."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from typing import Any

from scinumtools3.dip import Adapter, ExistingOutputPolicy, run_adapter
from snt_hub_runtime.dipl import evaluate_project
from snt_hub_runtime.output_plan import PlannedValues


ROOT = Path(__file__).resolve().parents[2]
REFERENCES = {
    "sedov_1d_cylindrical": Path("Exec/hydro_tests/Sedov/inputs.1d.cyl"),
    "sedov_1d_spherical": Path("Exec/hydro_tests/Sedov/inputs.1d.sph"),
    "sedov_2d_cartesian": Path("Exec/hydro_tests/Sedov/inputs.2d.cyl_in_cartcoords"),
    "sedov_2d_cylindrical": Path("Exec/hydro_tests/Sedov/inputs.2d.sph_in_cylcoords"),
    "sedov_2d_spherical": Path("Exec/hydro_tests/Sedov/inputs.2d.sph_in_sphcoords"),
    "sedov_3d_cartesian": Path("Exec/hydro_tests/Sedov/inputs.3d.sph"),
}
FIELDS = {
    "run.max_step": "max_step",
    "run.stop_time": "stop_time",
    "mesh.max_level": "amr.max_level",
    "mesh.regrid_interval": "amr.regrid_int",
    "hydro.cfl": "castro.cfl",
    "hydro.init_shrink": "castro.init_shrink",
    "hydro.change_max": "castro.change_max",
    "blast.radius": "problem.r_init",
    "blast.ambient_pressure": "problem.p_ambient",
    "blast.explosion_energy": "problem.exp_energy",
    "blast.ambient_density": "problem.dens_ambient",
    "blast.subcells": "problem.nsub",
    "eos.gamma": "eos.eos_gamma",
}


def load_environment(setup: str, bundle_root: Path = ROOT,
                     override_file: Path | None = None) -> Any:
    dipfile = Path(bundle_root) / "examples" / setup / "DIPfile"
    if setup not in REFERENCES or not dipfile.is_file():
        raise ValueError(f"Unknown Castro setup: {setup}")
    return evaluate_project(dipfile, override_file)


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        raise ValueError("Boolean value is invalid for this Castro setting")
    return f"{value:.12g}" if isinstance(value, float) else str(value)


def cell_axes(reference: str) -> tuple[str, ...]:
    match = re.search(r"^\s*amr\.n_cell\s*=\s*([^#\n]+)", reference, re.MULTILINE)
    if not match:
        raise ValueError("Castro reference is missing: amr.n_cell")
    cells = match.group(1).split()
    if not 1 <= len(cells) <= 3 or not all(cell.isdigit() for cell in cells):
        raise ValueError("Unsupported Castro base-grid dimension")
    return ("x", "y", "z")[:len(cells)]


def render_inputs(env: Any, reference: str) -> str:
    """Replace only reviewed keys while preserving all other upstream lines."""
    values = {key: format_value(env[key].value) for key in FIELDS}
    replacements = {key: values[path] for path, key in FIELDS.items()}
    replacements["amr.n_cell"] = " ".join(format_value(env[f"mesh.n{axis}"].value)
                                            for axis in cell_axes(reference))
    seen: set[str] = set()
    rendered = []
    pattern = re.compile(r"^(\s*)([A-Za-z_][\w.]*)\s*=\s*([^#\n]*?)(\s*(?:#.*)?)$")
    for line in reference.splitlines():
        match = pattern.match(line)
        if match and match.group(2) in replacements:
            key = match.group(2)
            if key in seen:
                raise ValueError(f"Duplicate Castro reference key: {key}")
            seen.add(key)
            original = match.group(3).split()
            replacement = replacements[key].split()
            try:
                unchanged = len(original) == len(replacement) and all(
                    Decimal(left) == Decimal(right)
                    for left, right in zip(original, replacement)
                )
            except InvalidOperation:
                unchanged = original == replacement
            if not unchanged:
                line = f"{match.group(1)}{key} = {replacements[key]}{match.group(4)}"
        rendered.append(line)
    missing = replacements.keys() - seen
    if missing:
        raise ValueError("Castro reference is missing: " + ", ".join(sorted(missing)))
    return "\n".join(rendered) + ("\n" if reference.endswith("\n") else "")


class CastroAdapter(Adapter):
    def __init__(self, reference: str):
        super().__init__()
        self.reference = reference

    def describe_outputs(self, env: Any, outputs: Any) -> None:
        fields = {**FIELDS, **{f"mesh.n{axis}": "amr.n_cell"
                               for axis in cell_axes(self.reference)}}
        for path, native in fields.items():
            outputs.add_node(env, f"inputs:{native}:{path}",
                             "inputs", path, path, active=True,
                             rule=f"Castro ParmParse {native}", origin="adapter:castro")

    def plan_resolved(self, env: Any, outputs: Any, context: Any) -> None:
        context.add_text("inputs", render_inputs(PlannedValues(outputs), self.reference))


def generate(output: Path, setup: str = "sedov_2d_cartesian",
             bundle_root: Path = ROOT, override_file: Path | None = None,
             source_root: Path | None = None) -> Path:
    env = load_environment(setup, bundle_root, override_file)
    source = Path(source_root) if source_root else Path(bundle_root).resolve().parent / "source"
    reference = (source / REFERENCES[setup]).read_text()
    run_adapter(env, CastroAdapter(reference), output, "environment.diph5",
                existing_output_policy=ExistingOutputPolicy.ReplaceRegistered)
    return Path(output)
