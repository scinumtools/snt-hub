# SNT Hub runtime

This Python package contains the setup steps shared by participating projects. It loads a local `project.json` and `setups.json`, checks the pinned source revision, builds a new setup in a temporary sibling directory, writes `setup-lock.json`, and publishes the directory only after project callbacks succeed. It also evaluates DIPL projects with optional overrides, checks new build locations, handles the common adapter CLI, and records local solver runs; projects supply their own render, input-preparation, build, and run-command callbacks.

Each project keeps its own DIPL model, renderer, and optional initial-input creator under `projects/<id>/`. The generic runtime does not know Arepo parameter names or run project scripts named by remote data. A project adapter calls `prepare_setup()` with explicit `render` and `prepare_inputs` callbacks. The [Arepo adapter](../projects/arepo/dipl/src/arepo_dipl/hub.py) is the first example.

To add a project, place `project.json`, `setups.json`, a pinned `source/` submodule, and an adapter package in `projects/<id>/`. Define each setup's capability as `complete` or `native-inputs-only`; implement a reviewed callback before marking it complete. The adapter package should depend on `snt-hub-runtime` and expose a command that SNT3's `hub setup` can invoke. The public registry and catalogue can consume the same project-local records.

## Local workspace contract

The runtime also accepts a fetched project laid out with `project.json`, `setups.json`, `dipl/`, and `source/` directly under a workspace root. The `hub.setup_manifest` field remains the canonical Hub-relative `projects/<id>/setups.json`; the loader checks its project ID without assuming that the workspace is inside a Hub checkout. Project adapters receive explicit `--bundle <workspace>/dipl` and `--source <workspace>/source` arguments, so their native input generation does not depend on the current directory or an application-data installation.

SNT3's proposed local fetch command owns workspace creation and its `.snthub/lock.json`. The runtime accepts a version-1 lock containing `project` (or `project_id`), `source_revision`, and a full `hub_revision`; it validates those fields against the project record. An optional `dipl_sha256` records the fetched adapter baseline; otherwise the runtime compares with `.snthub/hub/projects/<id>/dipl` if that pinned tree is present. Every setup verifies the pinned source commit, including `--inputs-only`, and writes the actual DIPL digest and source dirty state to `setup-lock.json`. If a baseline is available, the setup lock also states whether the DIPL package was edited. Edits remain allowed, but their outputs can be distinguished from the published adapter. The runtime's digest covers `dipl/pyproject.toml`, `dipl/examples/`, `dipl/profiles/`, and `dipl/src/`, excluding generated Python caches.

The local `fetch`, `build`, and `run` CLI commands are being implemented in SNT3. This package supplies setup orchestration plus shared workspace, lock, and executable checks for optional project build/run hooks. Arepo and QE now supply those hooks after one local build and smoke run each; the project adapters remain responsible for their compiler and solver commands.

Run `python3 scripts/check_project_bundles.py` from the repository root to check project records against the pinned source submodules, DIPL examples, and published parameter reports. The Pages build runs this check too.

See the [new-project guide](../docs/ADDING_PROJECT.md) for the record fields, command contract, evidence rules, and contributor checks.
