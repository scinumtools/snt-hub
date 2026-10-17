# Castro in SNT Hub

This independent bundle pins [Castro](https://github.com/AMReX-Astro/Castro) at `371ba40de0ef71963fa8f185d45c7d54e84ec041`. It models selected fields in six upstream hydro Sedov examples: two 1D, three 2D, and one 3D. The adapter writes each native `inputs` file and an `environment.diph5` snapshot. Unmodeled source lines, including the refinement indicators, remain in place.

```sh
snt hub fetch castro
snt hub examples
snt hub setup sedov_2d_cartesian
```

All six setups are self-contained as native input files. Building Castro separately requires the pinned AMReX and Microphysics submodules and a build with the corresponding `DIM`; the Hub does not yet offer a Castro build or run recipe. Settings parity is checked against every pinned source input, but solver execution and scientific results have not been validated. This work is independent of Castro's maintainers.
