# LAMMPS DIPL integration

This project pairs the pinned [LAMMPS](https://github.com/lammps/lammps) source at stable release `stable_30Sep2026` (`8de817dd79bfe4525d5d39246a212d833e6dee07`) with an independent DIPL adapter. The source is a Git submodule under [`source/`](source/); the adapter and parameter model live under [`dipl/`](dipl/). The registry record is [`project.json`](project.json), and [`setups.json`](setups.json) lists the reviewed examples.

The first scope is deliberately small: [`examples/melt/in.melt`](source/examples/melt/in.melt) and [`examples/min/in.min`](source/examples/min/in.min). Both create their atoms in the input script and need no external data files. Their shared DIPL schema covers geometry, Lennard-Jones pair settings, neighbors, velocity, and dynamics; the 2D example also models a minimization phase. The adapter writes `in.lammps` and `environment.diph5`. Its parity tests compare active LAMMPS commands and numeric arguments, not comments or disabled dump commands.

The local Hub workflow is:

```sh
mkdir lammps-study && cd lammps-study
snt hub fetch lammps
snt hub examples
snt hub setup lj_melt
snt hub build
snt hub run --setup runs/lj_melt
```

The optional `build` hook compiles the core `lmp` target with a serial CMake profile under `build/local/`. The `run` hook executes `lmp -in in.lammps` from a complete setup directory. See [`dipl/README.md`](dipl/README.md) for direct adapter commands and checks. The [`docs/parameters/`](docs/parameters/) reports show bundled values; an override produces a different evaluated environment that can be inspected from its DIPH5 snapshot.

This is an **independent external adapter**. LAMMPS itself does not parse DIPL, and no LAMMPS maintainer endorsement is implied. The adapter can eventually be replaced by direct SNT3 integration or static parameter generation where those fit the upstream code. Its current scope does not cover other force fields, packages, data files, workflows, or scientifically validated results.
