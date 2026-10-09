# QE PWscf DIPL adapter

The 27 recipes correspond to every input in QE 7.5's `test-suite/pw_scf/` directory. Each `DIPfile` loads [reusable PWscf schemas](profiles/schemas/README.md) and its own semantic settings. The adapter renders the supported namelists and cards to `pw.in` and writes `environment.diph5`. `si_scf` and `scf_gth` also stage checksummed pseudopotentials from the pinned source; the other 25 recipes require `--inputs-only`.

From the Hub root, with SciNumTools3 Python bindings installed:

```sh
python3 -m venv projects/quantum-espresso/dipl/.venv
projects/quantum-espresso/dipl/.venv/bin/python -m pip install -e hub -e 'projects/quantum-espresso/dipl[test]'
projects/quantum-espresso/dipl/.venv/bin/qe-dipl examples
projects/quantum-espresso/dipl/.venv/bin/qe-dipl setup --setup si_scf --output ./runs/si_scf
```

The generated `pw.in` uses local `./pseudo/` and `./tmp/` paths, so run `pw.x` from the generated directory after all prerequisites are present. The adapter does not build or execute QE. A per-run override file may tune modeled values, for example `system.ecutwfc = 16.0`; pass it with `--override-file`. Complete setup keeps the bundled pseudopotential selection. `--inputs-only` writes native input and DIPH5 without staging pseudopotentials. Bands and NSCF inputs also need the preceding calculation's scratch state before they can run.

The shared model covers the observed `&CONTROL`, `&SYSTEM`, and `&ELECTRONS` fields; atomic species and positions; explicit, band-path, automatic, and Gamma k-points; cell vectors; and explicit occupations. It does not cover the wider `pw.x` input catalogue, other QE executables, or an executable workflow for the dependent NSCF and bands cases. Numeric `celldm(1)` and `ecutwfc` values use QE's native bohr and Ry conventions. A broader integration should add explicit unit handling and new validation rules as new example families are added.

The [pattern inventory](docs/pw-scf-patterns.md) records how often each calculation and card form appears in the pinned set.

Species, atoms, cell vectors, explicit k-points, and band-path points are reusable DIPL list-item schemas. Optional namelist fields are composed through small schemas, so absent QE settings do not appear as artificial nodes in the parameter reports. The checked-in recipe settings come from the pinned references through `scripts/import_qe_pw_scf.py`; regenerate and review them when changing the source revision. An initial table-backed form caused the local SNT 0.9.2 parser to exit with code 139; the list-item model parses and generates correctly in the adjacent SNT3 build.
