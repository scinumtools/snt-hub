# Reusable PWscf schemas

These DIPL schemas describe the patterns shared by all 27 inputs in the pinned `test-suite/pw_scf/` directory. New example DIPfiles can load the same six files and supply their own values:

| File | Schemas | Native input |
| --- | --- | --- |
| `control.dip` | `qe_control` and optional field schemas | `&CONTROL` |
| `system.dip` | `qe_system` and optional field schemas | `&SYSTEM` |
| `electrons.dip` | Optional solver and mixing schemas | `&ELECTRONS` |
| `structure.dip` | Species, atom, and cell-vector schemas | Atomic and cell cards |
| `sampling.dip` | Explicit, band-path, and automatic sampling schemas | `K_POINTS` |
| `occupations.dip` | `qe_occupation_values` | `OCCUPATIONS` |

List collections apply a schema to each `species[]`, `atoms[]`, `cell_vectors[]`, `points[]`, or `path_points[]` item. The adapter preserves record order in the native cards. It checks `ntyp` and `nat`, species references, cell vectors for `ibrav=0`, and mode-specific k-point data. Optional namelist field schemas attach only when that field appears in an example; the empty `&ELECTRONS` namelist needs no artificial DIPL node.

The renderer supports the `scf`, `nscf`, and `bands` calculations and card variants present in the pinned set. It only generates inputs; NSCF and bands inputs need preceding solver state. DIPL attaches PUQ's AU Bohr radius to `celldm_1` and half a Hartree to QE energy parameters, matching QE's native bohr and Ry conventions while keeping the quantities dimensioned. Species masses use PUQ's atomic mass unit (`u`). Position and cell-vector coordinates retain their card-selected units (`alat`, `bohr`, `angstrom`, or `crystal`); their physical meaning depends on those mode fields.
