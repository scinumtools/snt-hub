import json
from pathlib import Path

import pytest

from qe_dipl import workflow
from snt_hub_runtime.setup import HubSetupError


def workspace_fixture(tmp_path, monkeypatch):
    root = tmp_path / "quantum-espresso"
    (root / "source").mkdir(parents=True)
    (root / "dipl").mkdir()
    (root / "project.json").write_text(json.dumps({"id": "quantum-espresso", "source_revision": "b" * 40}))
    (root / "setups.json").write_text(json.dumps({"schema_version": 1,
                                                 "setups": {"sample": {"capability": "complete"}}}))
    monkeypatch.setattr("snt_hub_runtime.workflow._pinned_revision", lambda *_: "b" * 40)
    monkeypatch.setattr(workflow, "_source_dirty", lambda *_: False)
    setup = root / "runs" / "sample"
    setup.mkdir(parents=True)
    (setup / "pw.in").write_text("&CONTROL /\n")
    (setup / "setup-lock.json").write_text(json.dumps({"project": "quantum-espresso",
        "source_revision": "b" * 40, "capability": "complete"}))
    return root, setup


def test_build_requires_nested_sources_and_uses_pw_target(tmp_path, monkeypatch):
    root, _ = workspace_fixture(tmp_path, monkeypatch)
    output = root / "build" / "local"
    with pytest.raises(HubSetupError, match="nested submodules"):
        workflow.build(root / "dipl", root / "source", root, output, "local")
    for path in ("mbd/CMakeLists.txt", "wannier90/src/wannier_lib.F90",
                 "devxlib/src/deviceXlib_mod.f90"):
        target = root / "source" / "external" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.touch()
    seen = []

    def fake_execute(command, cwd, log):
        seen.append(command)
        log.write_text("ok\n")
        if "--build" in command:
            executable = output / "cmake" / "bin" / "pw.x"
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"solver")

    monkeypatch.setattr(workflow, "execute", fake_execute)
    workflow.build(root / "dipl", root / "source", root, output, "local")
    assert ["--target", "qe_pw_exe"] == seen[1][seen[1].index("--target"):seen[1].index("--target") + 2]
    assert json.loads((output / "build-lock.json").read_text())["executable_sha256"]


def test_run_uses_pw_input_and_records_exit(tmp_path, monkeypatch):
    root, setup = workspace_fixture(tmp_path, monkeypatch)
    executable = root / "pw.x"
    executable.write_bytes(b"solver")

    class Result:
        returncode = 0

    seen = []

    def fake_run(command, **kwargs):
        seen.append((command, kwargs["cwd"]))
        return Result()

    monkeypatch.setattr("snt_hub_runtime.workflow.subprocess.run", fake_run)
    workflow.run(root / "dipl", root / "source", root, setup, executable)
    assert seen == [([str(executable), "-i", "pw.in"], setup)]
    assert json.loads((setup / "run-lock.json").read_text())["exit_status"] == 0
    with pytest.raises(HubSetupError, match="already"):
        workflow.run(root / "dipl", root / "source", root, setup, executable)
