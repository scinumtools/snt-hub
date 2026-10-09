# Add a code to SNT Hub

SNT Hub keeps each scientific code's original source, DIPL layer, registry record, and example recipes together under `projects/<id>/`. The [shared runtime](../hub/README.md) handles setup staging, source revision checks, and locks. A new project supplies its own parameter model and renderer.

## 1. Define the scope and pin the original code

Choose a short lowercase project ID. Add the code owner's canonical public repository as `projects/<id>/source`, pinned to a reviewed commit in `.gitmodules`. Treat that checkout as read-only. Keep DIPL models, adapters, and tests in `projects/<id>/dipl/`; do not add generated inputs, binaries, IC snapshots, or virtual environments to Git.

In `projects/<id>/README.md`, state the supported code revision, which inputs are modeled, which examples are covered, the adapter's provenance, and known limitations. Initial independent work does not imply support from the code's maintainers.

## 2. Add project-local records

Create `projects/<id>/project.json` using [Arepo's record](../projects/arepo/project.json) as a field example. Include the canonical `source_url`, full `source_revision`, source and adapter paths, current `integration_mode`, support and validation states, evidence links, limitations, and a review date. The registry builds directly from these records. Keep these three ideas separate:

| Field | What it says |
| --- | --- |
| `integration_mode` | How evaluated parameters reach the code now, such as `External adapter`. |
| `support` | `independent`, `maintainer-reviewed`, or `official`; record evidence before advancing it. |
| `validation` | `prototype`, `settings-parity`, `build-tested`, or `science-validated`; state the exact scope of the check. |

Add a `hub` section with the relative `runtime_package`, `adapter_package`, `adapter_executable`, `adapter_protocol`, `setup_manifest`, and example install/setup commands. The static [catalogue](https://scinumtools.github.io/snt-hub/catalog/v1.json) publishes these values with an immutable hub revision on GitHub Pages. The installed SNT3 CLI should reject an unpublished local catalogue revision.

Create `projects/<id>/setups.json` with `schema_version: 1` and a `setups` object. Each setup ID points to an actual `dipl/examples/<setup>/DIPfile`. Record an explicit source-example directory and a `capability`:

- `complete`: the recipe creates every required example input, including an IC file when the code needs one, and tests check the result.
- `native-inputs-only`: the adapter generates parameter files, but the IC or another prerequisite is supplied separately. `snt hub setup` requires `--inputs-only` for this state.

Do not infer a source-example name from the DIPL directory name. Arepo's `mhd_shock_tube` maps to the source's `mhd_shocktube_1d`; [its setup manifest](../projects/arepo/setups.json) makes that mapping explicit.

## 3. Implement the project adapter

Package the adapter under `projects/<id>/dipl/` with a `pyproject.toml` and a console-script executable. Depend on `snt-hub-runtime` and a compatible `scinumtools3` version. Use SNT3's adapter runner to render native files from an evaluated DIPfile. The project package owns code-specific names, units, tables, schedules, and validation; the shared runtime owns directory staging and setup locks.

Expose these executable arguments so the SNT3 `hub` module can call any project consistently:

```text
<adapter-executable> examples --bundle <absolute dipl path>
<adapter-executable> setup --bundle <absolute dipl path> --source <absolute source path>
                           --setup <example id> --output <absolute new directory>
                           [--inputs-only] [--override-file <path>]
```

The package should also offer a direct generation command for local development. The [Arepo implementation](../projects/arepo/dipl/src/arepo_dipl/hub.py) shows how to call `ProjectBundle.load()` and `prepare_setup()` with render and input-preparation callbacks. Do not put project scripts or parameter names in the generic runtime.

An IC creator may use a pinned upstream example script, a declared supplied asset, or another documented generator. Review its dependencies and any network access before marking the recipe `complete`. Run it in the staged output directory and check that its files match the evaluated input paths, format, and key physical settings. If some setup values are hard-coded in the creator, define a reviewed `ic_safe_overrides` list and reject other override targets until the creator can receive those values.

Support per-run override files without mutating the installed project bundle. Pass the override through SNT3's `add_override_file()` before parsing, include the same override when validating IC output, and record its contents and digest with the generated setup. An override file registered this way contains bare assignments; a `$override` directive is used for an inline region in ordinary DIPL source.

## 4. Prove the declared status

At minimum, test that each DIPL setup parses, its native outputs match the stated reference examples under documented comparison rules, and its output paths stay inside the generated directory. Test a complete setup from a clean location, including its IC file and `setup-lock.json`; test failure without a published partial directory. Record the pinned source commit and SNT3 version used for the check. A successful parameter comparison is **settings parity**, not a successful build or scientific validation.

Run the project tests and `cd website && npm run build`; confirm the project appears in the registry and `/catalog/v1.json`. Add links and a short explanation to the website only after the commands and evidence correspond to the checked-in records. The Pages workflow builds the registry and catalogue from the project data.

## 5. Grow beyond the first adapter

A native-file adapter is a practical first stage. Maintainers may later replace it with direct SNT3 C++ or Python access, the experimental C binding, or static parameter generation. Update `integration_mode`, the project guide, and evidence when that implementation actually changes. The optional, read-only [Parameter Viewer](https://scinumtools.github.io/snt3/integrations/viewer.html) can inspect the live DIPL project or generated DIPH5 snapshot at either stage.
