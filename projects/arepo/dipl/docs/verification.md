# Verification and maintainer workflow

## Packaged entry point

The reusable [hub runtime](../../../../hub/README.md) handles staging, source revision checks, and setup locks. The Arepo package supplies rendering and the reviewed IC recipe. From the repository root:

```bash
python3 -m venv projects/arepo/dipl/.venv
projects/arepo/dipl/.venv/bin/python -m pip install -e hub -e 'projects/arepo/dipl[test]'
projects/arepo/dipl/.venv/bin/python -m pytest projects/arepo/dipl/tests
projects/arepo/dipl/.venv/bin/arepo-dipl setup --setup mhd_shock_tube --output ./runs/mhd_shock_tube
```

The venv and output directories are ignored by Git. `arepo-dipl generate` handles all 16 native-input examples; `arepo-dipl setup` prepares a complete example only for a recipe marked `complete` in [`setups.json`](../../setups.json). The MHD recipe uses the pinned source's `create.py` to write `IC.hdf5`. Compilation remains separate and requires `SYSTYPE` or `Makefile.systype`, as described in [Arepo's build guide](../../source/documentation/source/running.md). No command here launches a simulation.

For a local build after setup, supply the generated config and paths to Arepo's Makefile, for example:

```sh
make -C projects/arepo/source SYSTYPE=YourSystem \
  CONFIG="$PWD/runs/mhd_shock_tube/Config.sh" \
  BUILD_DIR="$PWD/runs/mhd_shock_tube/build" \
  EXEC="$PWD/runs/mhd_shock_tube/Arepo" \
  PYTHON="$PWD/projects/arepo/dipl/.venv/bin/python"
```

## What the tests establish

- [`test_bundled_examples.py`](../tests/test_bundled_examples.py) generates all
  16 setups as separate pytest cases and compares active `Config.sh` and
  `param.txt` names and values directly with the bundled Arepo examples. It
  ignores comments, whitespace,
  ordering, and equivalent numeric spelling, but compares path strings
  exactly. It also checks softening-family counts against Arepo's native
  default or explicit `NSOFTTYPES`.
- [`test_rendering.py`](../tests/test_rendering.py) checks override loading,
  persistence, tagged export behavior, validation errors, output schedules,
  and native and table rendering after DIPH5 reload. Each full setup runs in
  a separate process because custom unit names are registered process-wide.
- [`test_override_units.py`](../tests/test_override_units.py) checks overrides
  expressed in hours, metres, and centimetres, including changes to a code
  unit base, and rejects incompatible dimensions.
- [`test_hub_cli.py`](../tests/test_hub_cli.py) checks recipe inventory, generation
  from another working directory, complete MHD setup with its IC file, and
  explicit refusal to treat unreviewed IC recipes as complete.
- [`table_inventory.json`](../tests/table_inventory.json) tracks the supplied
  numeric datasets. Tests compare rendered values with the upstream tables.

The checks establish equivalence of active settings for the bundled examples
within the numeric tolerances used by the tests; they do not compare comments,
ordering, or file bytes. Compiling with `-c` additionally checks the selected
configuration against the local compiler and libraries. Running a physical
simulation and checking its science outputs is a separate step.
