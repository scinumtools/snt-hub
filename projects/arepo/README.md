# Arepo DIPL integration

This directory keeps the original Arepo code and its optional DIPL parameter layer side by side:

- [`source/`](source/) is a Git submodule of the [canonical public Arepo repository](https://gitlab.mpcdf.mpg.de/vrs/arepo), pinned at `351aa8111a32e2e7433866bf8367ab7eba155d39`.
- [`dipl/`](dipl/) contains the DIPL model, Python adapter, bundled setup profiles, tests, and documentation. It generates Arepo's native inputs without changing the solver.
- [`project.json`](project.json) is this integration's public registry record. The website collects these records at build time.

The DIPL implementation was moved from the local `arepo-snt` integration fork, based on commit `7924a04` plus local uncommitted DIPL changes present in the linked checkout on 2026-10-09. Generated output, virtual environments, and caches were excluded. The fork is a provenance source; the submodule points to Arepo's canonical repository. This integration is independent and does not imply Arepo maintainer endorsement.

From the hub root:

```sh
git submodule update --init projects/arepo/source
projects/arepo/dipl/setup.sh -b -t
projects/arepo/dipl/setup.sh -g mhd_shock_tube
```

The generated `Config.sh`, `param.txt`, tables, and `environment.diph5` go under `projects/arepo/dipl/generated/`. See the [DIPL guide](dipl/README.md) for overrides and optional compilation. The regression tests compare active settings for the 16 bundled examples; they do not establish physical simulation results.

On 2026-10-09, the migrated suite passed locally against the pinned submodule with SciNumTools3 0.9.0: 38 tests and 28 subtests. The test environment came from the linked fork's existing virtual environment; `setup.sh -b` is the independent installation route for a fresh checkout.
