# Verification and maintainer workflow

## One entry point

[`setup.sh`](../setup.sh) resolves repository paths from its own location, so
it can be invoked from another working directory. From the repository root:

```bash
projects/arepo/dipl/setup.sh -b
projects/arepo/dipl/setup.sh -t
projects/arepo/dipl/setup.sh -g mhd_shock_tube
projects/arepo/dipl/setup.sh -c mhd_shock_tube
```

`-b` creates an isolated `projects/arepo/dipl/.venv` and installs the newest `scinumtools3>=0.9.0`,
pytest, and their dependencies from PyPI with pip. It requires package-index
access and does not read or write a local SciNumTools3 source tree. The venv
is ignored by Git. Later invocations use it by default; `PYTHON` explicitly
selects another interpreter. `-b -t` installs and then tests in one invocation.

`-t` runs the complete DIP test suite with pytest. `-g SETUP` generates native files into
`projects/arepo/dipl/generated/SETUP/`. `-c SETUP` regenerates the same setup and invokes
Arepo's Makefile with that `Config.sh`; build files and the executable go into
the same setup directory. `-g SETUP -c` is also accepted. `-c` requires a
configured `Makefile.systype` or `SYSTYPE` environment variable, as in
[Arepo's build guide](../../source/documentation/source/running.md). Set
`DIP_OUTPUT_ROOT` to place outputs
elsewhere. Compiling does not run a simulation.

The wrapper expects SciNumTools3 Python bindings with manifest overrides,
custom units, `Environment.select()`, value tags and metadata, and DIPH5
support. After `-b`, the direct test command is:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=projects/arepo/dipl/src \
  projects/arepo/dipl/.venv/bin/python -B -m pytest projects/arepo/dipl/tests
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
- [`test_setup_script.py`](../tests/test_setup_script.py) checks generation
  from another working directory and that compilation receives the selected
  config and isolated build paths. It uses a stand-in `make` so the test does
  not require an MPI compiler.
- [`table_inventory.json`](../tests/table_inventory.json) tracks the supplied
  numeric datasets. Tests compare rendered values with the upstream tables.

The checks establish equivalence of active settings for the bundled examples
within the numeric tolerances used by the tests; they do not compare comments,
ordering, or file bytes. Compiling with `-c` additionally checks the selected
configuration against the local compiler and libraries. Running a physical
simulation and checking its science outputs is a separate step.
