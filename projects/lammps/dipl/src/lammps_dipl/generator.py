"""Render the pinned self-contained Lennard-Jones examples from DIPL."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scinumtools3.dip import Adapter, DIP, ExistingOutputPolicy, run_adapter


ROOT = Path(__file__).resolve().parents[2]


class GenerationError(ValueError):
    pass


def load_environment(setup: str, bundle_root: Path = ROOT,
                     override_file: Path | None = None) -> Any:
    manifest = Path(bundle_root) / "examples" / setup / "DIPfile"
    if not manifest.is_file():
        raise GenerationError(f"Unknown LAMMPS setup: {setup}")
    dip = DIP()
    dip.add_project(manifest)
    if override_file is not None:
        dip.add_override_file(Path(override_file).resolve())
    return dip.parse()


def value(env: Any, name: str) -> Any:
    return env[name].value


def optional_value(env: Any, name: str) -> Any | None:
    try:
        return value(env, name)
    except Exception:
        return None


def number(value: float | int) -> str:
    return f"{float(value):.12g}"


def render_lammps(env: Any) -> str:
    dimension = int(value(env, "geometry.dimension"))
    lattice = value(env, "geometry.lattice_style")
    enforce_2d = bool(value(env, "dynamics.enforce_2d"))
    if (dimension, lattice, enforce_2d) not in ((3, "fcc", False), (2, "sq2", True)):
        raise GenerationError("Only the pinned 3D fcc and 2D sq2 LJ geometries are supported")
    for axis in "xyz":
        if value(env, f"geometry.{axis}hi") <= value(env, f"geometry.{axis}lo"):
            raise GenerationError(f"Invalid {axis}-axis box bounds")

    f = lambda path: number(value(env, path))
    yesno = lambda flag: "yes" if flag else "no"
    lines = ["# Generated from SNT Hub DIPL; evaluated values are in environment.diph5.",
             "units lj"]
    if dimension == 2:
        lines.append("dimension 2")
    lines.extend((
        "atom_style atomic",
        f"lattice {lattice} {f('geometry.lattice_density')}",
        "region box block " + " ".join(f(f"geometry.{axis}{bound}")
                                       for axis in "xyz" for bound in ("lo", "hi")),
        "create_box 1 box", "create_atoms 1 box",
        f"mass 1 {f('geometry.atom_mass')}",
        f"velocity all create {f('dynamics.initial_temperature')} "
        f"{value(env, 'dynamics.velocity_seed')} loop geom",
        f"pair_style lj/cut {f('interactions.cutoff')}",
        "pair_coeff 1 1 " + " ".join(f(f"interactions.{field}")
                                        for field in ("epsilon", "sigma", "cutoff")),
    ))
    if value(env, "interactions.shift_potential"):
        lines.append("pair_modify shift yes")
    lines.extend((
        f"neighbor {f('interactions.neighbor_skin')} bin",
        f"neigh_modify every {value(env, 'interactions.neighbor_every')} "
        f"delay {value(env, 'interactions.neighbor_delay')} "
        f"check {yesno(value(env, 'interactions.neighbor_check'))}",
        "fix 1 all nve",
    ))
    if enforce_2d:
        lines.append("fix 2 all enforce2d")
    lines.extend((f"thermo {value(env, 'dynamics.thermo_interval')}",
                  f"run {value(env, 'dynamics.run_steps')}"))
    after = optional_value(env, "minimization.thermo_interval_after_run")
    if after is not None:
        lines.extend((
            f"neigh_modify every {value(env, 'interactions.neighbor_every')} "
            f"delay {value(env, 'interactions.neighbor_delay')} "
            f"check {yesno(value(env, 'interactions.neighbor_check'))}",
            f"thermo {after}",
            "minimize " + " ".join(f(f"minimization.{field}") for field in
                                  ("energy_tolerance", "force_tolerance", "max_iterations",
                                   "max_evaluations")),
        ))
    return "\n".join(lines) + "\n"


class LammpsAdapter(Adapter):
    def plan(self, env: Any, context: Any) -> None:
        context.add_text("in.lammps", render_lammps(env))


def generate(output: Path, setup: str = "lj_melt", bundle_root: Path = ROOT,
             override_file: Path | None = None) -> Path:
    env = load_environment(setup, bundle_root, override_file)
    run_adapter(env, LammpsAdapter(), output, "environment.diph5",
                existing_output_policy=ExistingOutputPolicy.ReplaceRegistered)
    return Path(output)
