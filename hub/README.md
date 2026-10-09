# SNT Hub runtime

This Python package contains the setup steps shared by participating projects. It loads a local `project.json` and `setups.json`, checks the pinned source revision, builds a new setup in a temporary sibling directory, writes `setup-lock.json`, and publishes the directory only after project callbacks succeed.

Each project keeps its own DIPL model, renderer, and optional initial-input creator under `projects/<id>/`. The generic runtime does not know Arepo parameter names or run project scripts named by remote data. A project adapter calls `prepare_setup()` with explicit `render` and `prepare_inputs` callbacks. The [Arepo adapter](../projects/arepo/dipl/src/arepo_dipl/hub.py) is the first example.

To add a project, place `project.json`, `setups.json`, a pinned `source/` submodule, and an adapter package in `projects/<id>/`. Define each setup's capability as `complete` or `native-inputs-only`; implement a reviewed callback before marking it complete. The adapter package should depend on `snt-hub-runtime` and expose a command that SNT3's `hub setup` can invoke. The public registry and catalogue can consume the same project-local records.

See the [new-project guide](../docs/ADDING_PROJECT.md) for the record fields, command contract, evidence rules, and contributor checks.
