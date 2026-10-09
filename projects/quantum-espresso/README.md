# Quantum ESPRESSO in SNT Hub

This is an independent DIPL integration draft for [Quantum ESPRESSO](https://gitlab.com/QEF/q-e). The `source/` Git submodule is pinned to the QE 7.5 release commit `770a0b2d12928a67048e2f3da8d10d057e52179e`. The original source is not modified.

The current scope is **all 27 inputs in QE's pinned `test-suite/pw_scf/` directory**: self-consistent calculations, follow-up NSCF and bands inputs, and variants of electron controls, lattice descriptions, atomic structures, k-point modes, and occupations. The shared [PWscf schemas](dipl/profiles/schemas/README.md) describe their repeated concepts; each example supplies its own DIPL values. The adapter writes native `pw.in` and an evaluated `environment.diph5` snapshot. It does not compile or run `pw.x`.

Two recipes, `si_scf` (the upstream `scf-ncpp.in`) and `scf_gth`, are marked **complete** because their pseudopotentials are in the pinned source. Setup checks each asset's SHA-256, copies it into `pseudo/`, and creates the run's scratch directory. The other 25 recipes produce **native inputs only**: their referenced pseudopotentials are absent from the source tree, or the input is a follow-up step that needs previous calculation state. Use `--inputs-only` for those recipes and resolve prerequisites separately.

```sh
snt hub install quantum-espresso
snt hub examples quantum-espresso
snt hub setup quantum-espresso si_scf --output ./runs/si_scf
```

To change one run, pass `--override-file ./tuning.dip` to setup. The adapter evaluates the override before rendering, validates the supported cards, and records the exact override and SHA-256 in the setup output. For example:

```dipl
system.ecutwfc = 16.0
```

The pseudopotential filenames and `./pseudo/` directory are fixed for complete recipes. Changes to those values require a reviewed asset recipe; `--inputs-only` generates `pw.in` without staging pseudopotentials.

The [parameter references](docs/parameters/) are generated for all 27 DIPL projects with SNT's Brief++ reporter. They show bundled values; inspect a generated DIPH5 snapshot with the optional [Parameter Viewer](https://scinumtools.github.io/snt3/integrations/viewer.html) to see effective values after overrides. Regenerate the reports from the Hub root with `python3 scripts/generate_parameter_reports.py --project quantum-espresso --snt ../scinumtools3/build/bin/snt` while using the adjacent SNT3 build. Re-import the pinned native references with `python3 scripts/import_qe_pw_scf.py` after reviewing any source revision change.

This is an **external adapter**, not direct SNT3 support in QE. It can eventually be replaced by a maintainer-led C++, Python, C, or static-parameter integration. The current status is independent with **settings parity for the 27 pinned inputs**: input comparison and asset staging do not establish build success or scientifically validated results. See [`dipl/README.md`](dipl/README.md) for development commands and limitations.
