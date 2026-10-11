# OpenFOAM.com Hub integration

This bundle pins the OpenFOAM.com v2606 source at [`481094f`](source/). The source checkout is a Git submodule and remains unmodified. The DIPL adapter lives beside it in [`dipl/`](dipl/).

The demonstration covers ten upstream tutorials: icoFoam cavity, simpleFoam pitzDaily, interFoam dam break, rhoCentralFoam shock tube, solidDisplacementFoam plate-with-hole, overPimpleDyMFoam rotating square, buoyantBoussinesqPimpleFoam hot room, reactingFoam counterflow flame, mhdFoam Hartmann flow, and a twisting mesh column. DIPL exposes shared start/stop and write controls, output-format settings, adaptive time-step controls where used, finite-volume schemes, pressure-velocity coupling iterations, linear solver tolerances, and selected physical properties from each tutorial family. These map into `system/controlDict`, `system/fvSchemes`, `system/fvSolution`, and selected `constant/` dictionaries. The remaining native files and entries are staged from the pinned source unchanged.

The same DIPL contract also exposes selectable build configuration under `build.*`. Setup writes these choices to `build-profile.sh`, which sources the pinned v2606 `etc/bashrc` after applying the selected compiler, precision, label size, build mode, MPI, OpenMP, and architecture settings. This profile is a generated aid for a manual build; the Hub has not compiled OpenFOAM and does not yet provide a verified `snt hub build` hook.

From a local workspace with SNT3 0.9.3 or newer:

```sh
snt hub fetch openfoam
snt hub examples
snt hub setup cavity_ico --inputs-only
```

All ten recipes are currently `native-inputs-only`. The generated workspace contains the native tutorial files, `build-profile.sh`, and an `environment.diph5` snapshot. To build manually, set `OPENFOAM_SOURCE` to the pinned source checkout, source `build-profile.sh`, then run the upstream build command in that checkout. Setup does not generate meshes, run a solver, or validate scientific outputs. Follow each pinned tutorial's `Allrun` instructions in an OpenFOAM v2606 environment for the full workflow.

The project page links to [OpenFOAM.com](https://www.openfoam.com/) and its [tutorial guide](https://www.openfoam.com/documentation/tutorial-guide). This independent adapter does not imply maintainer endorsement.
