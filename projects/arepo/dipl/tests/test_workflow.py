import json
from pathlib import Path

import pytest

from arepo_dipl import workflow
from snt_hub_runtime.setup import HubSetupError


def workspace_fixture(tmp_path, monkeypatch):
    root = tmp_path / "arepo"
    (root / "source").mkdir(parents=True)
    (root / "dipl").mkdir()
    (root / "project.json").write_text(json.dumps({"id": "arepo", "source_revision": "a" * 40}))
    (root / "setups.json").write_text(json.dumps({"schema_version": 1,
                                                 "setups": {"sample": {"capability": "complete"}}}))
    monkeypatch.setattr("snt_hub_runtime.workflow._pinned_revision", lambda *_: "a" * 40)
    monkeypatch.setattr(workflow, "_source_dirty", lambda *_: False)
    setup = root / "runs" / "sample"
    setup.mkdir(parents=True)
    (setup / "Config.sh").write_text("HAVE_HDF5\n")
    (setup / "param.txt").write_text("InitCondFile IC\n")
    (setup / "setup-lock.json").write_text(json.dumps({"project": "arepo",
        "source_revision": "a" * 40, "capability": "complete"}))
    return root, setup


def test_build_uses_prepared_config_and_workspace_output(tmp_path, monkeypatch):
    root, setup = workspace_fixture(tmp_path, monkeypatch)
    seen = []

    def fake_execute(command, cwd, log, *, env=None):
        seen.append((command, cwd))
        assert env["SYSTYPE"] in {"Darwin", "Ubuntu"}
        Path(next(item.removeprefix("EXEC=") for item in command if item.startswith("EXEC="))).write_bytes(b"solver")
        log.write_text("built\n")

    monkeypatch.setattr(workflow, "execute", fake_execute)
    output = root / "build" / "sample" / "local"
    workflow.build(root / "dipl", root / "source", root, setup, output, "local")
    assert seen[0][1] == root / "source"
    assert f"CONFIG={setup / 'Config.sh'}" in seen[0][0]
    lock = json.loads((output / "build-lock.json").read_text())
    assert lock["setup_lock_sha256"] and lock["executable_sha256"]
    with pytest.raises(HubSetupError, match="new directory"):
        workflow.build(root / "dipl", root / "source", root, setup, output, "local")


def test_run_refuses_inputs_only_and_records_failure(tmp_path, monkeypatch):
    root, setup = workspace_fixture(tmp_path, monkeypatch)
    executable = root / "solver"
    executable.write_bytes(b"solver")
    lock_path = setup / "setup-lock.json"
    data = json.loads(lock_path.read_text())
    data["capability"] = "native-inputs-only"
    lock_path.write_text(json.dumps(data))
    with pytest.raises(HubSetupError, match="complete setup"):
        workflow.run(root / "dipl", root / "source", root, setup, executable)
    data["capability"] = "complete"
    lock_path.write_text(json.dumps(data))

    class Result:
        returncode = 7

    monkeypatch.setattr(workflow.subprocess, "run", lambda *args, **kwargs: Result())
    with pytest.raises(HubSetupError, match="run failed"):
        workflow.run(root / "dipl", root / "source", root, setup, executable)
    assert json.loads((setup / "run-lock.json").read_text())["exit_status"] == 7
