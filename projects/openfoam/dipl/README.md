# OpenFOAM.com DIPL adapter

This adapter covers ten pinned v2606 tutorials. Reusable schemas model shared `system/controlDict` controls, `system/fvSchemes` discretization choices, `system/fvSolution` coupling and linear solver tolerances, selected physical properties, and user-selectable `build.*` settings. The `openfoam:param` and `openfoam:config` tags identify runtime and build nodes for adapter discovery. The adapter stages each tutorial, rewrites only mapped native entries, and records those mappings in `environment.diph5`. It does not parse or generalize the full OpenFOAM dictionary language.

From the Hub repository root, with SciNumTools3 0.9.3 or newer available:

```sh
python3 -m venv projects/openfoam/dipl/.venv
projects/openfoam/dipl/.venv/bin/python -m pip install -e hub -e 'projects/openfoam/dipl[test]'
projects/openfoam/dipl/.venv/bin/openfoam-dipl examples
projects/openfoam/dipl/.venv/bin/openfoam-dipl setup --setup cavity_ico --output ./runs/cavity_ico --inputs-only
```

All recipes remain `native-inputs-only`: they prepare case files and a `build-profile.sh` from the same evaluated DIPL settings, but do not build OpenFOAM, generate meshes, or run solvers. For a manual build, set `OPENFOAM_SOURCE` to the pinned source checkout, source the generated profile, and run the upstream `Allwmake` command. This build path has not been compile-tested and is not a Hub `build` hook. For the standard SNT workspace flow, use `snt hub fetch openfoam`, then `snt hub setup <example> --inputs-only`. Source cases come from the `source/` Git submodule pinned in the project record. Setup locks record the source and DIPL revisions and the override provenance.

The project guide describes the ten cases and current scope. Each `settings.dip` starts from values in the native v2606 dictionaries. Tests cover modeled native-file parity across controls, schemes, solver settings, and physical properties; representative overrides; output-tree staging; and the local workspace contract. Most `fvSolution` settings, mesh controls, and initial/boundary field values are not yet modeled. No solver run or scientific-result validation is claimed.
