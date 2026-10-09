import json
from pathlib import Path

import pytest

from lammps_dipl import workflow
from snt_hub_runtime.setup import HubSetupError, ProjectBundle
from snt_hub_runtime.workflow import verify_executable


def workspace_fixture(tmp_path, monkeypatch):
    root = tmp_path / "lammps"
    (root / "source" / "cmake").mkdir(parents=True)
    (root / "source" / "cmake" / "CMakeLists.txt").touch()
    (root / "dipl").mkdir()
    (root / "project.json").write_text(json.dumps({"id": "lammps", "source_revision": "c" * 40}))
    (root / "setups.json").write_text(json.dumps({"schema_version": 1,
                                                 "setups": {"sample": {"capability": "complete"}}}))
    monkeypatch.setattr("snt_hub_runtime.workflow._pinned_revision", lambda *_: "c" * 40)
    monkeypatch.setattr(workflow, "_source_dirty", lambda *_: False)
    setup = root / "runs" / "sample"
    setup.mkdir(parents=True)
    (setup / "in.lammps").write_text("run 0\n")
    (setup / "setup-lock.json").write_text(json.dumps({"project": "lammps",
        "source_revision": "c" * 40, "capability": "complete"}))
    return root, setup


def test_build_uses_out_of_source_cmake_and_lmp_target(tmp_path, monkeypatch):
    root, _ = workspace_fixture(tmp_path, monkeypatch)
    output = root / "build" / "local"
    seen = []

    def fake_execute(command, cwd, log):
        seen.append(command)
        log.write_text("ok\n")
        if "--build" in command:
            executable = output / "cmake" / "lmp"
            executable.parent.mkdir(parents=True, exist_ok=True)
            executable.write_bytes(b"solver")

    monkeypatch.setattr(workflow, "execute", fake_execute)
    workflow.build(root / "dipl", root / "source", root, output, "local")
    assert seen[0][seen[0].index("-S") + 1] == str(root / "source" / "cmake")
    assert seen[1][seen[1].index("--target") + 1] == "lmp"
    lock = json.loads((output / "build-lock.json").read_text())
    assert lock["executable"] == "cmake/lmp"
    assert lock["build_log"] == "build.log"
    assert lock["compiler"] and lock["build_options"]
    assert verify_executable(ProjectBundle.load(root), root / "runs" / "sample",
                             output / "cmake" / "lmp") == output / "cmake" / "lmp"


def test_run_requires_complete_setup_and_records_solver_failure(tmp_path, monkeypatch):
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
        returncode = 4

    monkeypatch.setattr("snt_hub_runtime.workflow.subprocess.run", lambda *args, **kwargs: Result())
    with pytest.raises(HubSetupError, match="run failed"):
        workflow.run(root / "dipl", root / "source", root, setup, executable)
    assert json.loads((setup / "run-lock.json").read_text())["exit_status"] == 4
