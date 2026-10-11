# WRF idealized-case adapter

The package exposes `wrf-dipl` through the shared Hub adapter protocol. Ten setup IDs map to pinned WRF `test/em_*` examples; [`setups.json`](../setups.json) names each source namelist. Every setup stages `namelist.input` and `environment.diph5`. The `hill_2d` sounding is modeled as three surface values and a five-column imported DIPL table, then generated as native `input_sounding`; other profiles are staged unchanged from the pinned source. The baroclinic-wave `input_jet` is binary. The DIPL model covers selected useful controls, and unmodeled namelist keys retain their pinned upstream values. The source checkout is read-only.

From the Hub repository root, in an environment with SciNumTools3 and the shared Hub runtime:

```sh
python3 -m pip install -e hub -e 'projects/wrf/dipl[test]'
wrf-dipl examples
wrf-dipl setup --setup hill_2d --output ./runs/hill_2d --inputs-only
```

Use `--override-file PATH` for DIPL assignments such as `domains.dx = 1500 m`; omitted units use the field's declared native unit. Compatible overrides are converted back to the native value when the namelist is generated. The adapter validates grid dimensionality, 2D orientation where relevant, exclusive periodic/open x boundaries, and any initializer ID tied to a source profile. Changing a modeled value rewrites its native namelist entry. Other native settings remain pinned; review them before using a case outside its original purpose. WRF namelists can contain independent run-duration and end-time fields, so the adapter does not infer or rewrite their relationship.

With SNT3 0.9.3 or newer, `environment.diph5` records the modeled namelist and sounding surface mappings. `run_adapter_snapshot` reuses those values and the table retained in the snapshot. Replay still needs the pinned WRF source checkout to patch the original namelist and stage the unchanged profiles for the other cases.

`setup` requires `--inputs-only` because WRF's build and runtime assets have not been staged or verified. The convective-radiative case specifically needs radiation data prepared outside this adapter. No `snt hub build` or `snt hub run` capability is declared. A WRF build needs Fortran/C compilers and external libraries; follow the [official WRF guide](https://www2.mmm.ucar.edu/wrf/users/wrf_users_guide/build/html/index.html) for those steps. Tests compare generated namelists for all ten setups, compare unchanged staged assets byte-for-byte, verify the generated hill sounding against every pinned single-precision input value, then exercise overrides and setup locks.
