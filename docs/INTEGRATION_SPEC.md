---
title: "SNT Hub project integration specification"
subtitle: "Bundle contract and recommended DIPL organization"
author: "Ondrej Pego Jaura"
orcid: "0000-0002-5391-3714"
date: "10 October 2026"
lang: en
---

# Purpose and scope

SNT Hub publishes reproducible parameter integrations for established scientific codes. A Hub project pairs a **pinned original-code revision** with a **Hub-owned DIPL layer**, reviewed example recipes, and evidence of what has been checked. The original solver retains its own input format and numerical behavior. An external adapter may prepare those native inputs first; direct SNT3 integration or generated static parameters may replace that adapter later.

This document distinguishes the **bundle contract** required by the current Hub from **recommended model organization**. The recommendations are conventions for contributors, not new DIPL syntax or claims about every code. The [new-project guide](https://github.com/scinumtools/snt-hub/blob/main/docs/ADDING_PROJECT.md) describes the contribution steps; the [DIPL specification](https://scinumtools.github.io/snt3/dipl/index.html) defines language semantics.

The Hub release version in the PDF title comes from the repository's [VERSION](https://github.com/scinumtools/snt-hub/blob/main/VERSION) file. It labels this Hub publication; a project's pinned upstream source revision and the catalogue's schema version are independent identifiers.

# Bundle contract

Every published project has a stable lowercase ID and a directory `projects/<id>/`:

```text
projects/<id>/
  README.md                 scope, prerequisites, evidence, limitations
  project.json              registry record and Hub adapter capabilities
  setups.json               reviewed example IDs and capabilities
  source/                   pinned upstream Git submodule
  dipl/
    pyproject.toml          installable adapter package
    profiles/schemas/       reusable DIPL definitions
    examples/<example>/     one DIPfile and its local inputs per setup
    src/                    native-input adapter and optional build/run hooks
    tests/                  parity and workflow checks
  docs/parameters/          checked-in parsed parameter reports
```

`source/` is the code owner's pinned checkout. Hub development must not edit it to make an adapter work. `dipl/` is the integration layer and may be edited in a fetched local workspace; setup locks then record the edited state.

The project record identifies the canonical source URL and full revision, adapter package and executable, setup manifest, integration mode, maintainer support, validation level, evidence, limitations, and review date. Declare build and run capabilities only when the corresponding project hooks exist and have been exercised. The setup manifest maps each Hub example ID to its DIPL directory and exact upstream example path. A recipe is `complete` only if it prepares every required input or verified asset; otherwise mark it `native-inputs-only` and require the user's explicit `--inputs-only` choice.

The public registry derives from these records. **Integration mode**, **maintainer support**, and **validation evidence** are separate dimensions. A matching parameter file is settings parity; it is not proof of a successful solver run or scientific validation. See the [status definitions](https://scinumtools.github.io/snt-hub/integration-levels/).

# Recommended DIPL model structure

## Model the user's concepts first

Organize public parameter paths by the concepts a researcher chooses or inspects. Common top-level groups are `geometry`, `materials`, `physics`, `numerics`, `initial_state`, and `output`; use only groups that fit the code. Keep a stable, descriptive path for each concept. Within a group, put identity and selection fields first, then dimensions and physical values, then numerical controls, then derived or optional settings. Keep repeated entities as arrays or schema instances rather than numbered, unrelated fields.

The native file's section or command order belongs in the renderer. A DIPL tree may follow a native format where that makes the model clearer, but it should not be forced to mirror parser quirks. Record the mapping to native names in metadata or an adapter mapping so readers can move from a parameter to the generated file.

Do not expose adapter bookkeeping as ordinary scientific parameters. Output names, omission rules, and conditional native switches belong in an adapter policy or a dedicated binding mechanism when SNT3 provides one. If current tooling requires internal nodes, isolate and label them, keep them out of public parameter references where possible, and document a migration path. Never mix a renderer flag with a physical value under an indistinguishable path.

## Define schemas before example values

Put reusable type and validation definitions in `profiles/schemas/`. Group files by coherent domain, not by individual example or by arbitrary file length. A small project may need one schema file; a larger project can split units, geometry, physical models, numerical methods, and output settings. Name schemas for the concept they define. Prefer a small base schema plus explicit optional extensions over one schema with every possible field.

Within a schema, order declarations for a reader: identifying choices, required values, optional values, then derived values. Give each public field a meaningful type, unit where applicable, a concise `?descr`, and a condition or options list when there is a real constraint. Add a source URL or rationale when the meaning is code-specific or surprising. Describe the physical meaning and valid range; avoid repeating the field name as its description. Record native names when one exists. Constraints must reflect the pinned code, not a guessed universal rule.

For example, this defines a reusable concept and sets one example value:

```dip
$schema simulation_geometry
  box_length float
    !condition ({.} > 0)
    ?descr "Physical length of one side of the simulation box."

geometry : simulation_geometry
  box_length = 10.0
```

This is an organizational example; a real model should use the code's appropriate unit system and native mapping. Schema names and example values should remain separate so another setup can reuse the same constraint without copying it.

## Compose each example in a predictable order

An example directory has one `DIPfile` as its entry point. Register reusable schema files before the example's value file. A recommended reading order is:

1. Shared units and basic types, if the code needs custom definitions.
2. Reusable domain schemas, from broad structures to optional extensions.
3. Shared profiles or defaults that are genuinely common to several examples.
4. The example's settings and data sources.
5. Any derived values or output mappings that depend on the effective settings.

For instance:

```dip
code[]
  file = "../../profiles/schemas/geometry.dip"

code[]
  file = "../../profiles/schemas/numerics.dip"

code[]
  file = "settings.dip"
```

The actual `DIPfile` order must obey DIPL's loading rules. Register override files using DIPL's override mechanism so their assignments take effect before evaluation; do not assume that placing an ordinary file last has override semantics. Keep example-specific values in a short `settings.dip` or `profile.dip` and use additional files only for substantial tables or data. Explicitly map the Hub example ID to the pinned upstream input in `setups.json`, even if their names happen to match.

## Discover and express meaningful dependencies

When transcribing upstream examples, compare their input files, documentation, and setup scripts to find values that are determined by other choices: unit conversions, dimensions, complementary fractions, bounds, or repeated references to the same physical quantity. Record which values are independent user choices and which are consequences. Do not copy a dependent value into every example merely because the native format asks for it separately.

Use a DIPL expression and an explicit node reference when the relationship is deterministic, stable for the supported code revision, and short enough for a contributor to review. Prefer one authoritative input and derive the other value from it. For example, if the solver needs both a box length and its midpoint, a DIPL expression can derive the midpoint from the length instead of repeating two literals:

```dip
geometry
  box_length float = 10.0
  box_midpoint float = ( {?geometry.box_length} / 2 )
```

Document the meaning and units in the actual schema. Test that changing the independent value through an override updates the dependent value and generated native input. Check computed values against pinned upstream examples. Do not impose a formula where the two upstream values can legitimately vary independently; explain that choice in the project guide.

DIPL is a parameter model, not a replacement simulation program. Leave iterative numerical work, data processing, file generation, and solver algorithms in the scientific code or a reviewed adapter. A long chain of branches or calculations that is hard to inspect is a sign to simplify the model or move the logic to an appropriate component. Do not invent derived nodes solely to make a dependency graph look connected. Avoid hidden copies and cycles, and explain non-obvious conversions near their definitions. Where a native file needs another unit or representation, make the transformation visible in the model or renderer documentation and test the result.

## Keep provenance inspectable

The Hub's parameter reference shows evaluated paths, values, metadata, and source locations from a checked-in SNT report. Its graph distinguishes path hierarchy, schema supply, and **recorded evaluation reads**. A graph link is not automatically a scientific dependency; a literal setting may have no recorded reads. The report describes the bundled example, while a user's override can change effective values and dependencies. The generated DIPH5 snapshot and setup lock belong to each local run.

# Adapter and workspace behavior

The project adapter converts the evaluated model to the solver's native inputs. It owns code-specific formatting, file names, ordering, and checks. The shared Hub runtime owns source-revision checks, safe staging, workspace discovery, setup locks, and common adapter arguments. The SNT3 command should infer the project from a local `.snthub/lock.json` after `snt hub fetch PROJECT`.

The usual local flow is:

```sh
mkdir my-study && cd my-study
snt hub fetch PROJECT
snt hub examples
snt hub setup EXAMPLE
snt hub build
snt hub run --setup runs/EXAMPLE
```

`build` and `run` are optional project capabilities. A setup-specific build needs `--setup runs/EXAMPLE`; an inputs-only recipe needs `--inputs-only` at setup and cannot be treated as ready to run. A per-run `--override-file` changes evaluated values without editing the fetched bundle. Project documentation must state compilers, external assets, parallel launch requirements, and any missing workflow steps.

# Evidence and publication checklist

A project is ready for its declared registry state when its evidence matches its claims:

1. The source submodule, project record, setup manifest, and local examples agree on project ID and pinned revision.
2. Every published example parses with the supported SNT3 version. Public nodes have useful descriptions, units or unit conventions, constraints, native mappings where applicable, and source provenance.
3. Generated native settings match pinned upstream examples under documented comparison rules. Explain intentional differences and preserve path-sensitive values.
4. A complete recipe stages all required inputs, including checked assets or initial data, from a clean workspace. Tests cover a failed setup without a published partial directory and safe override behavior.
5. Build and run claims have separate recorded checks, with machine, version, prerequisites, and observed result. Scientific-result validation needs its own reference and tolerance criteria.
6. `python3 scripts/test_all.py` passes, parameter reports are regenerated, and the registry page links to the project guide, source, adapter, and parameter reference.

Independent adapters may be published with limited evidence when their scope and limitations are explicit. A project advances its support or validation label only after the corresponding review or check has occurred.

# Related resources

- [SNT3 source](https://github.com/scinumtools/snt3) and [SNT3 documentation](https://scinumtools.github.io/snt3/) cover the toolkit and current installation and CLI guidance.
- [SNT initiative](https://scinumtools.github.io/snt3/initiative.html) explains the broader collaboration and its goals.
- [DIPL specification](https://scinumtools.github.io/snt3/dipl/index.html) is authoritative for syntax and evaluation semantics; the [adapter guide](https://scinumtools.github.io/snt3/modules/dip/adapters.html) covers native-file generation.
- [C++ DIPL guide](https://scinumtools.github.io/snt3/modules/dip/basic-usage.html), [Python binding](https://scinumtools.github.io/snt3/integrations/python.html), and [static parameter generation](https://scinumtools.github.io/snt3/modules/dip/generation.html) describe paths beyond an external adapter.
- [Parameter Viewer](https://scinumtools.github.io/snt3/integrations/viewer.html) documents live DIPL and DIPH5 inspection.
- [SNT Hub source](https://github.com/scinumtools/snt-hub), [project registry](https://scinumtools.github.io/snt-hub/registry/), [integration levels and statuses](https://scinumtools.github.io/snt-hub/integration-levels/), and [new-project guide](https://github.com/scinumtools/snt-hub/blob/main/docs/ADDING_PROJECT.md) provide the current publishing context.

# Maintaining this document

The Markdown source is `docs/INTEGRATION_SPEC.md`; `docs/pandoc.yaml` holds the Pandoc build settings, includes the colored Hub logo, and reads `VERSION` for the title. Compile the website PDF by hand from the repository root:

```sh
pandoc --defaults docs/pandoc.yaml
```

Pandoc and XeLaTeX are required. To write a copy elsewhere, add `-o integration-spec.pdf`. The helper script runs the same defaults file:

```sh
scripts/build_integration_spec.sh
```

The defaults file writes `website/public/integration-spec.pdf`. Astro copies that file to `/snt-hub/integration-spec.pdf` during the GitHub Pages build. Commit the Markdown, Pandoc assets, and PDF together so the downloadable edition matches the current specification.
