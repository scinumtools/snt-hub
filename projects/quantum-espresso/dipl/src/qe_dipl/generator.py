"""Evaluate a DIPL setup and render the supported pw.x input subset."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scinumtools3.dip import Adapter, ExistingOutputPolicy, run_adapter
from snt_hub_runtime.dipl import evaluate_project


ROOT = Path(__file__).resolve().parents[2]


class GenerationError(ValueError):
    pass


def load_environment(setup: str = "si_scf", bundle_root: Path = ROOT, override_file: Path | None = None) -> Any:
    manifest = Path(bundle_root) / "examples" / setup / "DIPfile"
    if not manifest.is_file():
        raise GenerationError(f"Unknown or missing setup: {setup}")
    return evaluate_project(manifest, override_file)


def value(env: Any, name: str) -> Any:
    return env[name].value


def optional_value(env: Any, name: str) -> Any | None:
    try:
        return env[name].value
    except Exception:
        return None


def records(env: Any, path: str, fields: tuple[str, ...]) -> list[dict[str, Any]]:
    """Read contiguous DIPL list items as named records."""
    result: list[dict[str, Any]] = []
    for index in range(100000):
        try:
            env[f"{path}[{index}].{fields[0]}"]
        except Exception:
            break
        result.append({field: value(env, f"{path}[{index}].{field}") for field in fields})
    return result


def _quoted(text: str) -> str:
    if "\n" in text or "\r" in text:
        raise GenerationError("Namelist strings cannot contain newlines")
    return "'" + text.replace("'", "''") + "'"


def _float(number: float) -> str:
    return f"{float(number):.12g}"


def _relative_directory(text: str) -> str:
    path = Path(text)
    if path.is_absolute() or ".." in path.parts or str(path) in ("", "."):
        raise GenerationError(f"Output directory must be a safe relative path: {text!r}")
    return text


NAMELIST_FIELDS = {
    "CONTROL": ("calculation", "tstress", "tprnfor", "disk_io", "pseudo_dir", "outdir"),
    "SYSTEM": ("ibrav", "celldm_1", "nat", "ntyp", "ecutwfc", "nbnd", "use_all_frac",
               "input_dft", "vdw_corr", "force_symmorphic", "occupations"),
    "ELECTRONS": ("diago_thr_init", "diagonalization", "conv_thr", "diago_david_ndim",
                  "mixing_mode", "mixing_beta", "mixing_ndim"),
}


def _namelist(env: Any, name: str) -> list[str]:
    lines = [f"&{name}"]
    for field in NAMELIST_FIELDS[name]:
        node = f"{name.lower()}.{field}"
        item = optional_value(env, node)
        if item is None:
            continue
        native = "celldm(1)" if field == "celldm_1" else field
        if isinstance(item, str):
            encoded = _quoted(item)
        elif isinstance(item, bool):
            encoded = ".true." if item else ".false."
        elif isinstance(item, float):
            encoded = _float(item)
        else:
            encoded = str(item)
        lines.append(f"  {native} = {encoded},")
    return [*lines, "/"]


def render_pw(env: Any) -> str:
    """Render the named PWscf fields and card variants covered by the pinned SCF test set."""
    calculation = value(env, "control.calculation")
    if calculation not in ("scf", "nscf", "bands"):
        raise GenerationError(f"Unsupported PWscf calculation: {calculation}")
    pseudo_dir = _relative_directory(value(env, "control.pseudo_dir"))
    _relative_directory(value(env, "control.outdir"))
    species = records(env, "structure.species", ("symbol", "mass", "pseudo_file"))
    atoms = records(env, "structure.atoms", ("species", "x", "y", "z"))
    symbols = [item["symbol"] for item in species]
    pseudos = [item["pseudo_file"] for item in species]
    if not species or len(species) != value(env, "system.ntyp"):
        raise GenerationError("ATOMIC_SPECIES records must match ntyp")
    if not atoms or len(atoms) != value(env, "system.nat"):
        raise GenerationError("ATOMIC_POSITIONS records must match nat")
    if not {atom["species"] for atom in atoms}.issubset(symbols):
        raise GenerationError("Every atom must name a declared species")
    if len(set(symbols)) != len(symbols):
        raise GenerationError("Species labels must be unique")
    if any(not s or any(c.isspace() for c in s) for s in [*symbols, *(atom["species"] for atom in atoms), *pseudos]):
        raise GenerationError("Species labels and pseudopotential names must be single tokens")
    if any(Path(name).name != name for name in pseudos):
        raise GenerationError("Pseudopotential names must be filenames")

    ibrav = value(env, "system.ibrav")
    cell = records(env, "structure.cell_vectors", ("x", "y", "z"))
    if ibrav == 0:
        if len(cell) != 3 or optional_value(env, "structure.cell_units") is None:
            raise GenerationError("ibrav=0 requires three CELL_PARAMETERS vectors and units")
    elif ibrav in (1, 2):
        if optional_value(env, "system.celldm_1") is None or cell:
            raise GenerationError("ibrav=1 or 2 requires celldm(1) and no CELL_PARAMETERS card")
    else:
        raise GenerationError(f"Unsupported ibrav: {ibrav}")

    lines = ["! Generated by SNT Hub from an evaluated DIPL project."]
    for section in ("CONTROL", "SYSTEM", "ELECTRONS"):
        lines.extend(_namelist(env, section))
    if cell:
        lines.append(f"CELL_PARAMETERS ({value(env, 'structure.cell_units')})")
        lines.extend(f"  {_float(row['x'])} {_float(row['y'])} {_float(row['z'])}" for row in cell)
    lines.append("ATOMIC_SPECIES")
    lines.extend(f"  {item['symbol']} {_float(item['mass'])} {item['pseudo_file']}" for item in species)
    lines.append(f"ATOMIC_POSITIONS ({value(env, 'structure.position_units')})")
    lines.extend(
        f"  {atom['species']} {_float(atom['x'])} {_float(atom['y'])} {_float(atom['z'])}"
        for atom in atoms
    )
    mode = value(env, "sampling.mode")
    if mode == "gamma":
        lines.append("K_POINTS gamma")
    elif mode == "automatic":
        lines.append("K_POINTS automatic")
        lines.append("  " + " ".join(str(value(env, f"sampling.{field}")) for field in
                                 ("grid_x", "grid_y", "grid_z", "shift_x", "shift_y", "shift_z")))
    elif mode == "tpiba_b":
        points = records(env, "sampling.path_points", ("x", "y", "z", "segment_points"))
        if not points:
            raise GenerationError("K_POINTS tpiba_b needs at least one path point")
        lines.extend(("K_POINTS tpiba_b", f"  {len(points)}"))
        lines.extend(
            f"  {_float(point['x'])} {_float(point['y'])} {_float(point['z'])} {point['segment_points']}"
            for point in points
        )
    elif mode in ("tpiba", "crystal"):
        points = records(env, "sampling.points", ("x", "y", "z", "weight"))
        if not points:
            raise GenerationError("K_POINTS requires at least one explicit point")
        lines.extend((f"K_POINTS {mode}", f"  {len(points)}"))
        lines.extend(
            f"  {_float(point['x'])} {_float(point['y'])} {_float(point['z'])} {_float(point['weight'])}"
            for point in points
        )
    else:
        raise GenerationError(f"Unsupported K_POINTS mode: {mode}")
    occupations = optional_value(env, "system.occupations")
    bands = optional_value(env, "occupations.bands")
    if occupations == "from_input":
        if bands is None:
            raise GenerationError("occupations=from_input requires OCCUPATIONS values")
        bands = bands if isinstance(bands, list) else [bands]
        if optional_value(env, "system.nbnd") != len(bands):
            raise GenerationError("OCCUPATIONS count must match nbnd")
        lines.extend(("OCCUPATIONS", "  " + " ".join(_float(item) for item in bands)))
    elif bands is not None:
        raise GenerationError("OCCUPATIONS values require occupations=from_input")
    return "\n".join(lines) + "\n"


class PwAdapter(Adapter):
    def plan(self, env: Any, context: Any) -> None:
        context.add_text("pw.in", render_pw(env))


def generate(output: Path, setup: str = "si_scf", bundle_root: Path = ROOT,
             override_file: Path | None = None) -> Path:
    env = load_environment(setup, bundle_root, override_file)
    run_adapter(env, PwAdapter(), output, "environment.diph5",
                existing_output_policy=ExistingOutputPolicy.ReplaceRegistered)
    return Path(output)
