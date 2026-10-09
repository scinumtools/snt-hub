# Patterns in the pinned PWscf regression inputs

This inventory covers all 27 `.in` files in QE 7.5's `test-suite/pw_scf/`. Each source input has a DIPL setup under `dipl/examples/`, and the same schemas describe their repeated structure. Re-run `scripts/import_qe_pw_scf.py` after reviewing a new source revision, then run the parity tests and regenerate parameter reports.

| Pattern | Count | Shared model |
| --- | ---: | --- |
| SCF / NSCF / bands | 23 / 2 / 2 | `qe_control.calculation` |
| `ibrav` 2 / 1 / 0 | 22 / 4 / 1 | `qe_system`, optional `qe_system_celldm_1`, `qe_structure_cell` |
| Explicit `tpiba` / Gamma / band path / automatic / `crystal` k-points | 17 / 6 / 2 / 1 / 1 | `qe_sampling` plus mode-specific schema |
| `alat` / `bohr` / `angstrom` atom coordinates | 22 / 4 / 1 | `qe_structure.position_units`, reusable atom records |
| Empty / nonempty `&ELECTRONS` | 12 / 15 | Optional electron-field schemas, no placeholder nodes |
| `CELL_PARAMETERS` / `OCCUPATIONS` cards | 1 / 1 | Optional cell and occupation schemas |

All 27 use `ATOMIC_SPECIES` and `ATOMIC_POSITIONS`. Species, atoms, cell vectors, k-points, and path points are ordered DIPL list items. The renderer checks record counts and mode-specific requirements. Optional namelist fields are composed only in setups that use them, so parameter reports contain active settings rather than a catalogue of empty fields.

Only `si_scf` and `scf_gth` have every required pseudopotential in the pinned source tree. Their recipes stage checksummed source assets. The remaining 25 are `native-inputs-only`; four of those are NSCF or bands inputs that also require an earlier run's scratch state. Settings parity means the generated native values and cards agree with these reference inputs under the checked comparison. It does not imply that every setup is independently runnable or that solver results have been compared.

The parity test compares typed namelist values, species, positions, k-point modes and rows, cell vectors, and occupations. It ignores comments, whitespace, Fortran exponent spelling, and card order. It also excludes `pseudo_dir` and `outdir` from equality because the Hub deliberately writes local run-directory paths; pseudopotential names still have to agree.
