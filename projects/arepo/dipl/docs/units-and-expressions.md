# Units and expressions

## Selecting the code-unit bases

Each example's `DIPfile` explicitly loads one file defining
`code_units.length`, `code_units.mass`, and `code_units.velocity` before it
loads the derived unit definitions. There is no automatic selection based on
the setup name or its compile-time flags.

| Base profile | Setups | One code length | One code mass | One code velocity |
| --- | ---: | --- | --- | --- |
| [`standard_units.dip`](../profiles/standard_units.dip) | 10 | 1 cm | 1 g | 1 cm/s |
| [`cosmological_units.dip`](../profiles/cosmological_units.dip) | 5 | 1 kpc | 10¹⁰ solar masses | 1 km/s |
| [MHD shock tube `units.dip`](../examples/mhd_shock_tube/units.dip) | 1 | 1 cm | 1 g | 1 cm/s |

The five setups using the larger bases include the isolated-galaxy example;
the profile name describes its unit scale, not whether the simulation uses
cosmological integration. For example, the
[Alfvén-wave manifest](../examples/alfven_wave_1d/DIPfile) loads the standard
bases, while the [cosmological star-formation manifest](../examples/cosmological_star_formation/DIPfile)
loads the larger bases. The MHD shock tube keeps a local file to mirror its
original setup, although its current values equal the standard bases.

## Physical units and derived Arepo units

[`arepo_units.dip`](../profiles/schemas/arepo_units.dip) derives custom DIPL
units by referring to those selected values:

```dipl
$unit arepo_length = {?code_units.length}
$unit arepo_time = 1*arepo_length/arepo_velocity
$unit arepo_density = 1*arepo_mass/arepo_length3
```

The [simulation schema](../profiles/schemas/simulation.dip) then declares
`simulation.domain.box.size` in `arepo_length`. An override of `2 m` in an
idealised setup emits `BoxSize 200`, since each code length is one centimetre.
If the override also changes `code_units.length` to `2 cm`, `1 m` emits
`BoxSize 50` and `UnitLength_in_cm 2`. These are asserted in
[`test_override_units.py`](../tests/test_override_units.py), along with a
time conversion (`1 h` to `3600 s`) and rejection of a length set in seconds.
The tests reload DIPH5 and check that native rendering stays the same.

The three `code_units.*` values are physical quantities declared in `cm`,
`g`, and `cm/s`, matching Arepo's `UnitLength_in_cm`, `UnitMass_in_g`, and
`UnitVelocity_in_cm_per_s` parameters. DIPL resolves compatible overrides to
those declared units before the adapter reads the values.

The `arepo_*` names are derived DIPL units for values such as box sizes,
softening lengths, and densities. An override of a base unit is applied before
the derived units and dependent values are evaluated.

Choosing the larger unit bases does not enable cosmological integration.
[`native_controls.dip`](../profiles/native_controls.dip) sets
`ComovingIntegrationOn` from `simulation.time.coordinate`: `"scale_factor"`
enables it, while `"linear"` disables it.

## Expressions connect scientific inputs to native values

The [cosmological star-formation profile](../examples/cosmological_star_formation/profile.dip)
declares its initial redshift once and derives the start scale factor:

```dipl
initial_redshift = 127
begin float = ( 1 / ( 1 + {?simulation.time.initial_redshift} ) )
```

This yields `TimeBegin 0.0078125`. Overriding the redshift with `63` yields
`TimeBegin 0.015625`. The same profile derives the dark-energy density as
`1 - cosmology.matter_density` and dark-matter density as total matter minus
baryons. The [cosmology schema](../profiles/schemas/cosmology.dip) retains
their descriptions and validation conditions.

The [native controls](../profiles/native_controls.dip) are expressions too:
`simulation.time.coordinate = "scale_factor"` yields
`ComovingIntegrationOn 1`; `build.physics.cooling = true` yields
`CoolingOn 1`. These translations are DIPL values and therefore remain
visible, with their provenance, in `environment.diph5`.

Expressions are evaluated as the project is parsed. Set independent inputs
before their dependents in a profile; an override cannot introduce a forward
reference. See the [manifest and override guide](model-and-overrides.md) for
source ordering.
