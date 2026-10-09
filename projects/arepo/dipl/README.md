# DIPL / Arepo showcase

This directory is a semantic configuration layer for the 16 bundled Arepo
examples. DIPL describes the simulation and compile settings, their units,
validation rules, derived values, and provenance. The generator writes native
`Config.sh` and `param.txt` files, output schedules, scientific text tables,
and a reloadable `environment.diph5`. It does not modify the Arepo source tree
and needs no local SciNumTools3 source checkout. The original Arepo code is
pinned as the sibling `../source` Git submodule.

## Setup script

The executable [setup.sh](setup.sh) runs the dependency, test, generation, and
Arepo build workflow.
From the repository root:

```bash
projects/arepo/dipl/setup.sh -b
projects/arepo/dipl/setup.sh -t
projects/arepo/dipl/setup.sh -g mhd_shock_tube
projects/arepo/dipl/setup.sh -c mhd_shock_tube
projects/arepo/dipl/setup.sh -b -t -g mhd_shock_tube
```

`-b` creates `projects/arepo/dipl/.venv` and installs the newest `scinumtools3>=0.9.0`,
pytest, and their Python dependencies from PyPI. It does not use a local
SciNumTools3 directory. Later commands use that venv automatically. `-t` runs
the tests with pytest, `-g SETUP` generates the selected example, and `-c SETUP`
regenerates and compiles Arepo with its generated `Config.sh`. Results go to
`projects/arepo/dipl/generated/SETUP/`, including the compiled `Arepo` executable when `-c`
succeeds. Use `projects/arepo/dipl/setup.sh -h` for options. Compilation requires either a
configured `Makefile.systype` or a `SYSTYPE` value supported by the Arepo
Makefile; it does not launch a simulation. The script resolves repository
paths from its own location, so it also works when called by absolute path
from another directory. Set `PYTHON` to choose a Python 3 interpreter or
`DIP_OUTPUT_ROOT` to put generated files elsewhere. See the
[maintainer workflow](docs/verification.md) for build requirements and test
coverage.

To tune a setup, edit its own `overrides.dip` and regenerate it. For example,
[`alfven_wave_1d/overrides.dip`](examples/alfven_wave_1d/overrides.dip) can
contain:

```dipl
resources.wall_clock.limit = 1 h
simulation.domain.box.size = 2 m
```

The exported time limit is `3600` seconds; this example's centimetre code
length makes the exported box size `200`. The [unit override tests](tests/test_override_units.py)
exercise those conversions through a real setup manifest.

Each example's `DIPfile` explicitly selects its three physical code-unit
bases. Ten setups use centimetre/gram/centimetre-per-second bases from
[`standard_units.dip`](profiles/standard_units.dip); five use the larger
[`cosmological_units.dip`](profiles/cosmological_units.dip) bases; the MHD
shock tube has a local [`units.dip`](examples/mhd_shock_tube/units.dip) with
the standard numerical bases. The shared [`arepo_units.dip`](profiles/schemas/arepo_units.dip)
then derives `arepo_length`, `arepo_time`, and other units from whichever
bases the manifest loaded. These unit scales are separate from the switch
for cosmological integration; see [Units and expressions](docs/units-and-expressions.md).

## Read by topic

- [Model, schemas, and overrides](docs/model-and-overrides.md): manifests,
  reusable contracts, source ordering, and setup-specific tuning.
- [Units and expressions](docs/units-and-expressions.md): physical code bases,
  automatic conversion, scale-factor expressions, and derived native controls.
- [Native output, tables, and provenance](docs/native-outputs.md): tags, typed
  export rules, schedules, datasets, and DIPH5.
- [Verification and maintainer workflow](docs/verification.md): wrapper options,
  regression evidence, and the scope of the checks.

Concrete starting points are the [cosmological star-formation manifest](examples/cosmological_star_formation/DIPfile),
its [profile](examples/cosmological_star_formation/profile.dip), the
[simulation schema](profiles/schemas/simulation.dip), the
[custom-unit definitions](profiles/schemas/arepo_units.dip), and the
[tag-driven renderer](src/arepo_dipl/rendering.py).
