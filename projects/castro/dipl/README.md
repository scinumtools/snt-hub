# Castro DIPL adapter

Six Sedov models expose the termination time and step count, dimension-specific base grid size, two AMR controls, hydro timestep controls, Sedov blast parameters, and gamma-law EOS. They cover 1D cylindrical and spherical, 2D Cartesian, cylindrical and spherical, and 3D Cartesian configurations. The renderer reads each pinned upstream input and changes only these keys, preserving all other settings and comments.

Install this package with `hub/` and SNT3, then run `castro-dipl examples` or `castro-dipl setup --setup sedov_2d_cartesian --output runs/sedov_2d_cartesian`. An override file can change modeled values, for example `blast.explosion_energy = 2.0`. Run each generated `inputs` file with the corresponding Castro Sedov executable built for its dimension. Solver build and run are outside this adapter's validated scope.
