import json

import pytest

from snt_hub_runtime.setup import HubSetupError, ProjectBundle
from snt_hub_runtime.workflow import digest, verify_executable


def test_workspace_executable_must_match_build_and_setup_locks(tmp_path):
    bundle = ProjectBundle(tmp_path, {"id": "example", "source_revision": "a" * 40}, {})
    setup = tmp_path / "runs" / "first"
    setup.mkdir(parents=True)
    (setup / "setup-lock.json").write_text("first")
    build = tmp_path / "build" / "first" / "local"
    build.mkdir(parents=True)
    executable = build / "solver"
    executable.write_bytes(b"solver")
    (build / "build-lock.json").write_text(json.dumps({
        "project": "example", "source_revision": "a" * 40,
        "setup_lock_sha256": digest(setup / "setup-lock.json"),
        "executable": str(executable), "executable_sha256": digest(executable),
    }))
    assert verify_executable(bundle, setup, executable) == executable
    (setup / "setup-lock.json").write_text("changed")
    with pytest.raises(HubSetupError, match="different setup"):
        verify_executable(bundle, setup, executable)
