# Add a code to SNT Hub

SNT Hub keeps each scientific code's original source, DIPL layer, registry record, and example recipes together under `projects/<id>/`. The [integration specification](INTEGRATION_SPEC.md) states the bundle contract and recommended node and schema organization. The [shared runtime](../hub/README.md) handles setup staging, source revision checks, and locks. A new project supplies its own parameter model and renderer.

## 1. Define the scope and pin the original code

Choose a short lowercase project ID. Add the code owner's canonical public repository as `projects/<id>/source`, pinned to a reviewed commit in `.gitmodules`. Treat that checkout as read-only. Keep DIPL models, adapters, and tests in `projects/<id>/dipl/`; do not add generated inputs, binaries, IC snapshots, or virtual environments to Git.

In `projects/<id>/README.md`, state the supported code revision, which inputs are modeled, which examples are covered, the adapter's provenance, and known limitations. Initial independent work does not imply support from the code's maintainers.

## 2. Add project-local records

Create `projects/<id>/project.json`. Include the canonical `source_url`, full `source_revision`, source and adapter paths, current `integration_mode`, support and validation states, evidence links, limitations, and a review date. The registry builds directly from these records. Keep these three ideas separate:

The [public status guide](https://scinumtools.github.io/snt-hub/integration-levels/) defines the labels and evidence expected for each state.

| Field | What it says |
| --- | --- |
| `integration_mode` | How evaluated parameters reach the code now, such as `External adapter`. |
| `support` | `independent`, `maintainer-reviewed`, or `official`; record evidence before advancing it. |
| `validation` | `prototype`, `settings-parity`, `build-tested`, or `science-validated`; state the exact scope of the check. |

Add a `hub` section with the relative `runtime_package`, `adapter_package`, `adapter_executable`, `adapter_protocol`, `setup_manifest`, and example fetch/setup commands. The static [catalogue](https://scinumtools.github.io/snt-hub/catalog/v1.json) publishes these values with an immutable hub revision on GitHub Pages. SNT3 should reject an unpublished local catalogue revision.

Create `projects/<id>/setups.json` with `schema_version: 1` and a `setups` object. Each setup ID points to an actual `dipl/examples/<setup>/DIPfile`. Record an explicit source-example path (a directory or input file) and a `capability`:

- `complete`: the recipe creates every required example input, including an IC file when the code needs one, and tests check the result.
- `native-inputs-only`: the adapter generates parameter files, but the IC or another prerequisite is supplied separately. `snt hub setup` requires `--inputs-only` for this state.

Do not infer a source-example name from the DIPL directory name. Record the exact upstream example path in `setups.json`, since the Hub setup ID and upstream name may differ.

## 3. Implement the project adapter

Package the adapter under `projects/<id>/dipl/` with a `pyproject.toml` and a console-script executable. Depend on `snt-hub-runtime` and a compatible `scinumtools3` version. Use SNT3's adapter runner to render native files from an evaluated DIPfile. The project package owns code-specific names, units, tables, schedules, and validation; the shared runtime owns directory staging and setup locks.

Expose these executable arguments so the SNT3 `hub` module can call any project consistently:

```text
<adapter-executable> examples --bundle <absolute dipl path>
<adapter-executable> setup --bundle <absolute dipl path> --source <absolute source path>
                           --setup <example id> --output <absolute new directory>
                           [--inputs-only] [--override-file <path>]
```

The package should also offer a direct generation command for local development. Use the shared [`adapter_main()`](../hub/src/snt_hub_runtime/cli.py) for the standard command arguments and [`evaluate_project()`](../hub/src/snt_hub_runtime/dipl.py) to parse a DIPfile with an optional override. Call `ProjectBundle.load()` and `prepare_setup()` with render and input-preparation callbacks. Use `new_build_output()` from the shared workflow module before creating a build directory. Do not put project scripts or parameter names in the generic runtime.

Also test the adapter with the planned local workspace layout: copy `project.json`, `setups.json`, and `dipl/` to a new workspace root, place the pinned source checkout at `source/`, and invoke the same adapter command with `--bundle <workspace>/dipl --source <workspace>/source`. Keep the checked-in `hub.setup_manifest` path unchanged; the shared loader accepts it in both layouts. The setup lock should record the pinned source commit even for `--inputs-only`, plus the actual DIPL digest and source dirty state. A `.snthub/lock.json` written by the future `fetch` command may supply the Hub commit and fetched DIPL baseline.

An IC creator may use a pinned upstream example script, a declared supplied asset, or another documented generator. Some codes need a pseudopotential or similar prerequisite instead of a separate IC file; stage required assets with recorded checksums. Review asset licences, dependencies, and any network access before marking a recipe `complete`. Prepare inputs in the staged output directory and check that their files match evaluated paths, formats, and key physical settings. If setup values are hard-coded in a creator, define a reviewed `ic_safe_overrides` list and reject other override targets until the creator can receive those values.

Support per-run override files without mutating the fetched project bundle. Pass the override through SNT3's `add_override_file()` before parsing and include the same override when validating IC output. Pass its path as `override_file` to `prepare_setup()`; the shared runtime checks that it stays unchanged and records its contents and digest with the generated setup. An override file registered this way contains bare assignments; a `$override` directive is used for an inline region in ordinary DIPL source.

## 4. Prove the declared status

At minimum, test that each DIPL setup parses, its native outputs match the stated reference examples under documented comparison rules, and its output paths stay inside the generated directory. Test a complete setup from a clean location, including its IC file and `setup-lock.json`; test failure without a published partial directory. Record the pinned source commit and SNT3 version used for the check. A successful parameter comparison is **settings parity**, not a successful build or scientific validation.

Run `python3 scripts/test_all.py`; it checks project bundles, runs all Python suites, and builds the website. Confirm the project appears in the registry and `/catalog/v1.json`. Add links and a short explanation to the website only after the commands and evidence correspond to the checked-in records. The Pages workflow checks the bundles and builds the registry and catalogue from the project data.

Publish parsed parameter data beside the project under `projects/<id>/docs/parameters/<setup>.json`. Generate each file from its bundled `DIPfile` with `snt report --project ... --format json`, using a report-enabled SNT build. Include all setup IDs in `setups.json`, keep generated source paths repository-relative, and regenerate the reports whenever a DIPL model changes. The website builds its own browsable reference from the checked-in Brief++ JSON at `/projects/<id>/parameters/<setup>/`; old `.html` URLs redirect there. Its project page lists the available reports. Use [the shared generator](../scripts/generate_parameter_reports.py) for every project. The reports show bundled example values, so direct users to DIPH5 inspection for per-run overrides.

## 5. Grow beyond the first adapter

A native-file adapter is a practical first stage. Maintainers may later replace it with direct SNT3 C++ or Python access, the experimental C binding, or static parameter generation. Update `integration_mode`, the project guide, and evidence when that implementation actually changes. The optional, read-only [Parameter Viewer](https://scinumtools.github.io/snt3/integrations/viewer.html) can inspect the live DIPL project or generated DIPH5 snapshot at either stage.

Local `snt hub build` and `snt hub run` are optional project capabilities, separate from the DIPL setup adapter. An absent `hub.build` or `hub.run` object in `project.json` means unsupported. Add the corresponding versioned capability and project adapter command only after a reviewed, testable build or run recipe exists; see the command proposal in `PROPOSAL/SNT_HUB_COMMAND_PROPOSAL.md` for the intended protocol. A `complete` setup means its input preparation is complete; it does not establish that the solver was built, ran, or produced validated science.
