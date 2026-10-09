# Model, schemas, and overrides

## How a setup is assembled

Each [setup manifest](../examples/cosmological_star_formation/DIPfile) names
its DIPL code files, optional `.dipt` data sources, and one
[`overrides.dip`](../examples/cosmological_star_formation/overrides.dip). Paths
are relative to the manifest. The generator discovers manifests under
[`examples/`](../examples/) and loads the chosen one with `DIP.add_project()` in
[`generator.py`](../src/arepo_dipl/generator.py). There is no Python list of
parameters or per-setup loader.

The manifest loads the export contract, its chosen physical code-unit bases,
and the shared derived `arepo_*` units first. It then loads shared schemas,
reusable baselines, the setup profile, derived native controls, and any
dataset imports. This order lets later expressions see the selected profile's
effective values, including overrides. The unit-base file is selected by the
manifest, not by the generator or a runtime mode switch; see
[Units and expressions](units-and-expressions.md).

## Shared schemas, concrete values

A [simulation schema](../profiles/schemas/simulation.dip) declares the box size
as `float arepo_length`, requires it to be positive, and maps it to Arepo's
`BoxSize` parameter:

```dipl
size float arepo_length
  !condition ({.} > 0 arepo_length)
  ?native "BoxSize"
  !tags ["arepo:param"]
```

The [cosmological star-formation profile](../examples/cosmological_star_formation/profile.dip)
instantiates that contract and supplies `size = 7500 arepo_length`. Other
setups reuse the schema with different values. The
[`arepo_build` schema](../profiles/schemas/build.dip) does the same for
compile-time capabilities: for example, `build.physics.cooling = true` in the
star-formation profile becomes `COOLING` in `Config.sh`. Its fields contain
descriptions, native names, options, and impact notes. Schema-level `?url`
and `?see` point to relevant Arepo guide sections; these links document
native semantics, not authorship of the DIPL schema.

The shared contracts are grouped by concern under
[`profiles/schemas/`](../profiles/schemas/): build, simulation, resources,
input, output, snapshots, gravity, hydrodynamics, mesh, cosmology, cooling,
star formation, and analysis. Profiles can add example-local fields where the
shared contract is insufficient.

## Tune an existing setup

Edit only that setup's `overrides.dip`. Its body is unwrapped because the
manifest registers it under `overrides[]`:

```dipl
resources.wall_clock.limit = 1 h
simulation.domain.box.size = 2 m
```

The first assignment becomes `TimeLimitCPU 3600`; the second becomes a box
size expressed in the setup's code-length unit. See the executable
[unit override tests](../tests/test_override_units.py). Values are replaced
at declaration time, so [expressions](units-and-expressions.md) downstream
use the tuned input. Prefer independent inputs such as
`simulation.time.initial_redshift` over overriding a derived output directly.

An override may target an existing scalar or explicit collection member. It
cannot add a node or instantiate an absent physics schema. A target may be
assigned only once across the project. Unknown paths, duplicate targets,
type declarations, property declarations, incompatible units, and violations
of the target's constraints are errors. Empty or comment-only override files
are valid. Dependencies must already exist when their expression is first
declared; overrides do not enable forward references.

The effective value and override provenance survive in `environment.diph5`:

```python
env.select("?resources.wall_clock.limit")[0].override
env["resources.wall_clock.limit"].provenance.override_code
```

The manifest, override, and persistence behavior is checked in
[`test_rendering.py`](../tests/test_rendering.py).
