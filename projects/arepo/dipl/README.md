# DIPL / Arepo showcase

This directory is a semantic configuration layer for the 16 bundled Arepo
examples. DIPL describes the simulation and compile settings, their units,
validation rules, derived values, and provenance. The generator writes native
`Config.sh` and `param.txt` files, output schedules, scientific text tables,
and a reloadable `environment.diph5`. It does not modify the Arepo source tree
and needs no local SciNumTools3 source checkout. The original Arepo code is
pinned as the sibling `../source` Git submodule.

This adapter is the first compatibility layer. A future Arepo integration could consume evaluated SNT3 parameters directly through C++ or Python, use the experimental C binding, or include generated static parameters instead of generating `Config.sh` and `param.txt` through this wrapper. Those paths require code-owner review and are not implemented here. The optional, read-only [Parameter Viewer](https://scinumtools.github.io/snt3/integrations/viewer.html) can inspect these live `DIPfile` projects or a generated `environment.diph5` snapshot; the snapshot does not contain full source text.

With a source-built `snt` that has the optional viewer enabled, for example:

```bash
snt view projects/arepo/dipl/examples/mhd_shock_tube/DIPfile
snt view projects/arepo/dipl/generated/mhd_shock_tube/environment.diph5
```

Generate the selected example before opening its snapshot. The Python adapter package does not install the optional graphical `snt view` executable; follow the viewer guide for its build requirements.

## Package and setup commands

From the hub root, install the shared runtime and the Arepo adapter in an isolated Python environment:

```bash
python3 -m venv projects/arepo/dipl/.venv
projects/arepo/dipl/.venv/bin/python -m pip install -e hub -e 'projects/arepo/dipl[test]'
projects/arepo/dipl/.venv/bin/arepo-dipl examples
projects/arepo/dipl/.venv/bin/arepo-dipl generate --setup mhd_shock_tube --output projects/arepo/dipl/generated/mhd_shock_tube
projects/arepo/dipl/.venv/bin/arepo-dipl setup --setup mhd_shock_tube --output ./runs/mhd_shock_tube
```

`generate` writes native files and DIPH5 for any of the 16 setups. `setup` writes to a fresh directory and also prepares ICs for recipes marked `complete`; currently this is `mhd_shock_tube`. For another example, use `setup --setup NAME --output DIR --inputs-only` until its IC recipe is reviewed. The complete MHD setup runs the pinned Arepo `create.py`, checks the resulting `IC.hdf5` against DIPL settings, and writes `setup-lock.json`. Existing output directories are rejected. The local `snt hub fetch arepo` / `snt hub setup mhd_shock_tube` flow uses this project bundle and adapter entry point.

To tune one run without editing the bundled model, write an unwrapped override file and pass it to setup:

```dipl
resources.wall_clock.limit = 1800 s
hydrodynamics.courant_factor = 0.25
```

```bash
projects/arepo/dipl/.venv/bin/arepo-dipl setup --setup mhd_shock_tube \
  --override-file ./tuning.dip --output ./runs/mhd_tuned
```

The same flag is accepted by `generate` and by the SNT Hub setup contract. The effective settings and override provenance go into `environment.diph5`; setup also copies the exact override text to `input-overrides.dip` and records its SHA-256 in `setup-lock.json`. Duplicate targets across the bundled and per-run override files are rejected. The pinned MHD IC creator fixes physical values, so its complete recipe currently permits only `resources.wall_clock.limit` and `hydrodynamics.courant_factor` overrides. Other override targets fail without publishing an output directory; use `--inputs-only` for broader parameter experiments until the IC creator and checks support them.

The adapter package accepts `--bundle PATH` and `--source PATH` when invoked by SNT from a local workspace. To test locally, run `projects/arepo/dipl/.venv/bin/python -m pytest projects/arepo/dipl/tests`. The adapter's `build` hook invokes Arepo's Makefile with the generated `Config.sh`; its `run` hook starts the executable as a direct MPI singleton. See the [maintainer workflow](docs/verification.md).

For the local Hub workspace, the same adapter entry point accepts `--bundle <workspace>/dipl --source <workspace>/source`; `project.json` and `setups.json` sit at the workspace root. A workspace-layout integration test exercises the complete MHD recipe through this interface. Build and run also receive `--workspace`, write logs and locks, and require a complete setup. Only `mhd_shock_tube` has a local solver smoke check so far.

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
