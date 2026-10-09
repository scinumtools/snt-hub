"""Import and compare the pinned QE PWscf regression inputs.

This intentionally supports the syntax present in test-suite/pw_scf at the
pinned source revision. Unknown fields or cards fail rather than disappearing.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "source"
EXAMPLES = ROOT / "dipl" / "examples"
SCHEMAS = ("control", "system", "electrons", "structure", "sampling", "occupations")
CARD_NAMES = {"ATOMIC_SPECIES", "ATOMIC_POSITIONS", "K_POINTS", "CELL_PARAMETERS", "OCCUPATIONS"}
ASSIGNMENT = re.compile(r"([A-Za-z_][A-Za-z_0-9]*(?:\(\d+\))?)\s*=\s*('[^']*'|\"[^\"]*\"|[^,\s]+)")
HEADER = re.compile(r"^(ATOMIC_SPECIES|ATOMIC_POSITIONS|K_POINTS|CELL_PARAMETERS|OCCUPATIONS)\b(.*)$", re.I)
FIELD_TYPES = {
    "control": {"calculation": str, "tstress": bool, "tprnfor": bool, "disk_io": str,
                "pseudo_dir": str, "outdir": str},
    "system": {"ibrav": int, "celldm(1)": float, "nat": int, "ntyp": int, "ecutwfc": float,
               "nbnd": int, "use_all_frac": bool, "input_dft": str, "vdw_corr": str,
               "force_symmorphic": bool, "occupations": str},
    "electrons": {"diago_thr_init": float, "diagonalization": str, "conv_thr": float,
                  "diago_david_ndim": int, "mixing_mode": str, "mixing_beta": float,
                  "mixing_ndim": int},
}
BASE_FIELDS = {
    "control": {"calculation", "pseudo_dir", "outdir"},
    "system": {"ibrav", "nat", "ntyp", "ecutwfc"},
    "electrons": set(),
}


def _number(raw: str) -> float:
    return float(raw.replace("D", "e").replace("d", "e"))


def _decode(raw: str, kind: type) -> Any:
    if kind is str:
        if not (raw.startswith("'") and raw.endswith("'")):
            raise ValueError(f"Expected a quoted Fortran string: {raw}")
        return raw[1:-1].replace("''", "'")
    if kind is bool:
        if raw.lower() not in (".true.", ".false."):
            raise ValueError(f"Expected a Fortran boolean: {raw}")
        return raw.lower() == ".true."
    if kind is int:
        return int(raw)
    return _number(raw)


def _mode(header: str) -> str:
    return header.strip().strip("(){}").strip().lower()


def parse_native(path: Path) -> dict[str, Any]:
    """Parse only the QE input syntax covered by the pinned PWscf test set."""
    lines = []
    for source_line in Path(path).read_text().splitlines():
        line = source_line.split("#", 1)[0].split("!", 1)[0].strip()
        if line:
            lines.append(line)
    sections: dict[str, dict[str, Any]] = {}
    index = 0
    while index < len(lines) and lines[index].startswith("&"):
        name = lines[index][1:].lower()
        if name not in FIELD_TYPES or name in sections:
            raise ValueError(f"Unexpected namelist {name} in {path}")
        index += 1
        body = []
        while index < len(lines) and lines[index] != "/":
            body.append(lines[index])
            index += 1
        if index == len(lines):
            raise ValueError(f"Unterminated namelist {name} in {path}")
        index += 1
        joined = "\n".join(body)
        fields: dict[str, Any] = {}
        for match in ASSIGNMENT.finditer(joined):
            key, raw = match.groups()
            key = key.lower()
            if key not in FIELD_TYPES[name] or key in fields:
                raise ValueError(f"Unknown or duplicate {name}.{key} in {path}")
            fields[key] = _decode(raw, FIELD_TYPES[name][key])
        remainder = ASSIGNMENT.sub("", joined).replace(",", "").strip()
        if remainder:
            raise ValueError(f"Unparsed {name} input in {path}: {remainder}")
        sections[name] = fields
    if set(sections) != set(FIELD_TYPES):
        raise ValueError(f"Missing required namelist in {path}: {set(FIELD_TYPES) - set(sections)}")

    cards: dict[str, tuple[str, list[str]]] = {}
    while index < len(lines):
        match = HEADER.match(lines[index])
        if not match:
            raise ValueError(f"Unexpected card data in {path}: {lines[index]}")
        name, suffix = match.groups()
        name = name.upper()
        if name in cards:
            raise ValueError(f"Repeated card {name} in {path}")
        index += 1
        data = []
        while index < len(lines) and not HEADER.match(lines[index]):
            data.append(lines[index])
            index += 1
        cards[name] = (_mode(suffix), data)
    if not {"ATOMIC_SPECIES", "ATOMIC_POSITIONS", "K_POINTS"}.issubset(cards):
        raise ValueError(f"Missing required PWscf cards in {path}")

    ntyp, nat = sections["system"]["ntyp"], sections["system"]["nat"]
    species = []
    for line in cards["ATOMIC_SPECIES"][1]:
        parts = line.split()
        if len(parts) != 3:
            raise ValueError(f"Malformed ATOMIC_SPECIES row in {path}: {line}")
        species.append((parts[0], _number(parts[1]), parts[2]))
    if len(species) != ntyp:
        raise ValueError(f"ntyp mismatch in {path}")
    positions = []
    for line in cards["ATOMIC_POSITIONS"][1]:
        parts = line.split()
        if len(parts) != 4:
            raise ValueError(f"Malformed ATOMIC_POSITIONS row in {path}: {line}")
        positions.append((parts[0], *map(_number, parts[1:])))
    if len(positions) != nat:
        raise ValueError(f"nat mismatch in {path}")

    mode, data = cards["K_POINTS"]
    mode = mode or "tpiba"
    sampling: dict[str, Any] = {"mode": mode}
    if mode == "gamma":
        if data:
            raise ValueError(f"Gamma K_POINTS has rows in {path}")
    elif mode == "automatic":
        if len(data) != 1 or len(data[0].split()) != 6:
            raise ValueError(f"Malformed automatic K_POINTS in {path}")
        sampling["grid"] = tuple(map(int, data[0].split()))
    elif mode in ("tpiba", "crystal", "tpiba_b"):
        count = int(data[0]) if data else -1
        if len(data) != count + 1:
            raise ValueError(f"K_POINTS count mismatch in {path}")
        points = []
        for line in data[1:]:
            parts = line.split()
            if len(parts) != 4:
                raise ValueError(f"Malformed K_POINTS row in {path}: {line}")
            fourth = int(parts[3]) if mode == "tpiba_b" else _number(parts[3])
            points.append((*map(_number, parts[:3]), fourth))
        sampling["points"] = points
    else:
        raise ValueError(f"Unsupported K_POINTS mode {mode} in {path}")

    cell = None
    if "CELL_PARAMETERS" in cards:
        unit, rows = cards["CELL_PARAMETERS"]
        if len(rows) != 3:
            raise ValueError(f"CELL_PARAMETERS must have three vectors in {path}")
        cell = {"units": unit, "vectors": [tuple(map(_number, row.split())) for row in rows]}
        if any(len(row) != 3 for row in cell["vectors"]):
            raise ValueError(f"Malformed CELL_PARAMETERS vector in {path}")
    occupations = None
    if "OCCUPATIONS" in cards:
        occupations = [_number(part) for row in cards["OCCUPATIONS"][1] for part in row.split()]
    return {"namelists": sections, "species": species, "positions": positions,
            "position_units": cards["ATOMIC_POSITIONS"][0], "sampling": sampling,
            "cell": cell, "occupations": occupations}


def _dipl(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value)
    return repr(value)


def render_settings(parsed: dict[str, Any], source_name: str) -> str:
    """Emit semantic DIPL values using the shared schemas, not native syntax."""
    sections = parsed["namelists"]
    lines = [f"# Imported from pinned QE test-suite/pw_scf/{source_name}."]
    for section in ("control", "system", "electrons"):
        fields = sections[section]
        if not fields and section == "electrons":
            continue
        extras = sorted(set(fields) - BASE_FIELDS[section])
        names = ([f"qe_{section}"] if section != "electrons" else []) + [
            f"qe_{section}_{'celldm_1' if key == 'celldm(1)' else key}" for key in extras
        ]
        lines.append(f"\n{section} : {', '.join(names)}")
        for key, item in fields.items():
            lines.append(f"  {'celldm_1' if key == 'celldm(1)' else key} = {_dipl(item)}")
        if section == "control":
            lines.extend(('  pseudo_dir = "./pseudo/"', '  outdir = "./tmp/"'))

    names = ["qe_structure"] + (["qe_structure_cell"] if parsed["cell"] else [])
    lines.append(f"\nstructure : {', '.join(names)}")
    lines.append(f"  position_units = {_dipl(parsed['position_units'])}")
    for symbol, mass, pseudo in parsed["species"]:
        lines.extend(("  species[]", f"    symbol = {_dipl(symbol)}",
                      f"    mass = {_dipl(mass)}", f"    pseudo_file = {_dipl(pseudo)}"))
    for symbol, x, y, z in parsed["positions"]:
        lines.extend(("  atoms[]", f"    species = {_dipl(symbol)}",
                      f"    x = {_dipl(x)}", f"    y = {_dipl(y)}", f"    z = {_dipl(z)}"))
    if parsed["cell"]:
        lines.append(f"  cell_units = {_dipl(parsed['cell']['units'])}")
        for x, y, z in parsed["cell"]["vectors"]:
            lines.extend(("  cell_vectors[]", f"    x = {_dipl(x)}",
                          f"    y = {_dipl(y)}", f"    z = {_dipl(z)}"))

    sampling = parsed["sampling"]
    mode = sampling["mode"]
    extra_schema = {"automatic": "qe_sampling_automatic", "tpiba_b": "qe_sampling_band_path",
                    "tpiba": "qe_sampling_explicit", "crystal": "qe_sampling_explicit"}.get(mode)
    names = ["qe_sampling"] + ([extra_schema] if extra_schema else [])
    lines.append(f"\nsampling : {', '.join(names)}")
    lines.append(f"  mode = {_dipl(mode)}")
    if mode == "automatic":
        for name, item in zip(("grid_x", "grid_y", "grid_z", "shift_x", "shift_y", "shift_z"), sampling["grid"]):
            lines.append(f"  {name} = {item}")
    elif mode in ("tpiba", "crystal", "tpiba_b"):
        for x, y, z, fourth in sampling["points"]:
            lines.extend(("  path_points[]" if mode == "tpiba_b" else "  points[]",
                          f"    x = {_dipl(x)}", f"    y = {_dipl(y)}", f"    z = {_dipl(z)}",
                          f"    {'segment_points' if mode == 'tpiba_b' else 'weight'} = {_dipl(fourth)}"))
    if parsed["occupations"] is not None:
        values = ", ".join(_dipl(item) for item in parsed["occupations"])
        lines.extend(("\noccupations : qe_occupation_values", f"  bands = [{values}]"))
    return "\n".join(lines) + "\n"


def setup_id(source_name: str) -> str:
    return "si_scf" if source_name == "scf-ncpp.in" else source_name.removesuffix(".in").lower().replace("-", "_")


def import_all() -> dict[str, Any]:
    """Write every pinned PWscf regression input as a Hub DIPL example."""
    recipes: dict[str, dict] = {}
    for path in sorted((SOURCE / "test-suite" / "pw_scf").glob("*.in")):
        if path.name.startswith("benchmark"):
            continue
        parsed = parse_native(path)
        name = setup_id(path.name)
        directory = EXAMPLES / name
        directory.mkdir(parents=True, exist_ok=True)
        manifest = [f"# Pinned upstream input: test-suite/pw_scf/{path.name}."]
        for component in SCHEMAS:
            manifest.extend(("code[]", f'  file = "../../profiles/schemas/{component}.dip"', ""))
        manifest.extend(("code[]", '  file = "settings.dip"', ""))
        (directory / "DIPfile").write_text("\n".join(manifest))
        (directory / "settings.dip").write_text(render_settings(parsed, path.name))
        pseudos = [item[2] for item in parsed["species"]]
        assets = []
        for pseudo in pseudos:
            source_file = SOURCE / "pseudo" / pseudo
            if source_file.is_file():
                assets.append({"source": f"pseudo/{pseudo}", "file": pseudo,
                               "sha256": sha256(source_file.read_bytes()).hexdigest()})
        complete = (len(assets) == len(pseudos) and
                    parsed["namelists"]["control"]["calculation"] == "scf")
        recipe: dict[str, Any] = {
            "source_example": f"test-suite/pw_scf/{path.name}",
            "capability": "complete" if complete else "native-inputs-only",
            "required_pseudos": pseudos,
        }
        if complete:
            recipe["pseudo_assets"] = assets
        recipes[name] = recipe
    return {"schema_version": 1, "setups": recipes}
