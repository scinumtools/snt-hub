# LAMMPS DIPL adapter

Four pinned, self-contained examples use reusable schemas in [`profiles/schemas/lj.dip`](profiles/schemas/lj.dip). `lj_melt` renders a 3D melt, `lj_minimize_2d` renders a 2D run and minimization, and `flow_couette` and `flow_poiseuille` render distinct 2D channel-flow drivers. Each produces `in.lammps` and an inspectable `environment.diph5`.

From the Hub repository root, install this package beside the shared runtime in a Python environment that has SciNumTools3:

```sh
python3 -m venv projects/lammps/dipl/.venv
projects/lammps/dipl/.venv/bin/python -m pip install -e hub -e 'projects/lammps/dipl[test]'
projects/lammps/dipl/.venv/bin/lammps-dipl examples
projects/lammps/dipl/.venv/bin/lammps-dipl setup --setup lj_melt --output ./runs/lj_melt
```

`setup` refuses an existing output directory and records the pinned source, evaluated DIPL tree, and generated files in `setup-lock.json`. These input scripts create atoms themselves, so all four recipes are `complete`. A bare DIPL override file can be passed with `--override-file PATH`; the accepted text and digest are recorded beside the generated input.

With SNT3 0.9.3 or newer, `environment.diph5` also stores the resolved mapping from DIPL fields to LAMMPS commands, including decisions for optional dimension, potential-shift, and 2D-fix commands. `run_adapter_snapshot` can regenerate `in.lammps` from that saved plan without loading the original DIPL profiles.

For an SNT Hub workspace, the adapter receives `--bundle <workspace>/dipl`, `--source <workspace>/source`, and, for build/run, `--workspace <workspace>`. The build profile configures LAMMPS CMake with MPI and OpenMP disabled and writes the `lmp` executable and build lock under `build/local/`; the run command accepts only complete setups and records its command, executable hash, logs, and exit status. The build needs CMake, a C++17 compiler, and a build tool. Tests cover active-command parity with all four pinned upstream examples and the local workspace contract.
