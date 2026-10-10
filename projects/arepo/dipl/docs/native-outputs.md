# Native output, tables, and provenance

## Tags and recorded output plans

The [output policy](../src/arepo_dipl/output_policy.py) discovers values tagged
`arepo:config` for `Config.sh` and `arepo:param` for `param.txt`. Each exported
node declares its Arepo name with `?native`, so adding a normal scalar
parameter requires a DIPL declaration rather than a Python catalog entry.
True config booleans emit bare flags; false config booleans are omitted.
Runtime booleans emit `0` or `1`.

The adapter records one mapping for each native key, including inactive
mappings. A mapping contains its source path or typed calculated value,
resolved decision, rule, origin, and dependencies. The DIPH5 snapshot keeps
this plan for inspection and replay. Ordinary scalar mappings need no Python
rule. Exceptional omission and feature rules live in
[`output_policy.py`](../src/arepo_dipl/output_policy.py); example-specific
choices use explicit plan replacements with both origins recorded. They are
not artificial DIPL parameters.

For example, [`code_units.length`](../profiles/standard_units.dip) is declared
in centimetres and names its output `UnitLength_in_cm` with `?native`. DIPL
normalizes compatible overrides to the node's declared units before export. The
[selected unit-base profile](units-and-expressions.md) likewise declares mass
in grams and velocity in centimetres per second. The
[mesh refinement schema](../profiles/schemas/mesh.dip) exports
`ReferenceGasPartMass` only when `build.mesh.refinement` is enabled. The
[build schema](../profiles/schemas/build.dip) leaves `NSOFTTYPES` inactive by
default, because this Arepo source uses six families when the flag is absent;
the four setups that explicitly use two families activate its mapping.

The policy checks missing native names, missing or non-boolean feature
dependencies, and duplicate active native keys. It sorts by full DIPL path for
reproducible output. `?requires` remains descriptive metadata; the adapter
explicitly defines output predicates. Indexed `SofteningComovingTypeN`,
`SofteningMaxPhysTypeN`, and `SofteningTypeOfPartTypeN` are also recorded in the
plan because Arepo uses flat indexed keys for those families. Derived switches
such as `CoolingOn` are typed calculated mappings, with their scientific
inputs listed as dependencies.

## Output schedules and scientific datasets

Five bundled setups use typed [output schedule tables](../examples/cosmological_star_formation/output_schedule.dipt).
Cosmological schedules contain `scale_factor` and `write_flag`; linear-time
schedules contain `time` in `arepo_time` and `write_flag`. The generator writes
the schedule to `output.schedule.filename` when enabled. A matching time
column is required. Generated paths must stay within the output directory
and may not collide. Disabling a schedule does not remove an older schedule
file from a previous generation.

Scientific numeric tables live in `.dipt` files and are registered as named
`sources[]` in each manifest. For example, the
[gravity-only manifest](../examples/cosmological_gravity_only/DIPfile)
registers mass-reference tables; its [tables.dip](../examples/cosmological_gravity_only/tables.dip)
imports them under `datasets` and declares output filenames. The
[table renderer](../src/arepo_dipl/tables.py) uses SciNumTools3's ordered
`inspect_table()` result and emits native text layouts at 17 significant digits.
The order survives DIPH5 loading. There are 15 distinct additional numeric
tables and 16 imports across the setups, plus the five schedules and shared cooling
table. Binary initial conditions and external generator configurations keep
their existing roles.

The output plan also records which dataset and schedule files are active;
the adapter renders their contents from the retained DIPL tables.

## DIPH5 snapshot

[`generate()`](../src/arepo_dipl/generator.py) uses the SciNumTools3 adapter
runner to write `Config.sh`, `param.txt`, the selected tables and schedule, and
`environment.diph5`. Its `ReplaceRegistered` policy stages fresh outputs before
replacing generated files and preserves an existing build.
DIPH5 stores evaluated values, units, custom units, schema metadata, tags,
source and override provenance, collections, table data, and the resolved
output plan. A fresh process can load the snapshot and render the native files
again without the DIPL sources or re-evaluating output policy.
The [roundtrip tests](../tests/test_rendering.py) verify that behavior.
