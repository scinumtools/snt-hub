# WRF meteorology DIPL integration

This bundle pins the official [WRF source](https://github.com/wrf-model/WRF) to release `v4.8.0` (`06d4240ae989cc3e50af412bb472df3d9048783c`) as a Git submodule in [`source/`](source/). Its independent DIPL adapter lives in [`dipl/`](dipl/). [`project.json`](project.json) is the registry record; [`setups.json`](setups.json) maps Hub setup IDs to exact upstream examples.

The initial scope covers ten idealized WRF cases: baroclinic wave, convective-radiative equilibrium, gravity current, Held-Suarez, hill flow, quarter-circle shear supercell, sea breeze, squall lines in both orientations, and tropical cyclone. A shared schema describes selected time, grid, dynamics, boundary, and initializer controls. The renderer keeps every other upstream namelist entry unchanged, so each default generation is byte-for-byte identical to its pinned namelist. It also stages the case's checked-in sounding or jet profile when one exists, plus an inspectable `environment.diph5`. The baroclinic jet profile is binary and is copied without text conversion.

```sh
mkdir wrf-study && cd wrf-study
snt hub fetch wrf
snt hub examples
snt hub setup hill_2d --inputs-only
```

All ten recipes are **native-inputs-only**. WRF needs a configured build and additional runtime files before `ideal.exe` and `wrf.exe` can run. In particular, the convective-radiative case requires radiation assets beyond its staged sounding. This bundle does not currently offer Hub build or run hooks. The adapter accepts DIPL overrides for modeled fields, for example `domains.dx = 1500`, and records them in the setup lock. Case-specific checks preserve the 2D orientation and pinned initializer identity. See the [adapter guide](dipl/README.md) and [parameter reports](docs/parameters/) for details.

The current check is **settings parity** for ten pinned namelists and their staged source assets, not a successful WRF run or scientific validation. Five families remain outside the present bundle: LES, single-column model, fire, real-data, and ESMF coupling. Their extra profiles, data, and workflow requirements deserve separate recipes. The adapter is independent of WRF maintainers. A future direct SNT3 integration or generated static parameters may replace the external namelist adapter.
