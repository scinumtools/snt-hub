"""The shared runner must never publish a partial project setup."""

import json
import subprocess

import pytest

from snt_hub_runtime import HubSetupError, ProjectBundle, prepare_setup


def _local_source(project):
    source = project / "source"
    source.mkdir()
    subprocess.run(["git", "init", "-q", str(source)], check=True)
    subprocess.run(["git", "-C", str(source), "-c", "user.name=Hub Test",
                    "-c", "user.email=hub@example.invalid", "commit", "-q",
                    "--allow-empty", "-m", "fixture"], check=True)
    revision = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    return source, revision


def test_render_failure_leaves_destination_unpublished(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    source, revision = _local_source(project)
    (project / "project.json").write_text(json.dumps({"id": "test", "source_revision": revision}))
    (project / "setups.json").write_text(json.dumps({
        "schema_version": 1,
        "setups": {"example": {"capability": "native-inputs-only"}},
    }))
    bundle = ProjectBundle.load(project)
    output = tmp_path / "output"

    def failing_render(context):
        (context.stage / "partial.txt").write_text("incomplete")
        raise RuntimeError("render failed")

    with pytest.raises(RuntimeError, match="render failed"):
        prepare_setup(bundle, "example", output, source_root=source,
                      render=failing_render, inputs_only=True)

    assert not output.exists()
    assert not list(tmp_path.glob(".test-setup-*"))


def test_workspace_bundle_accepts_hub_relative_manifest_and_records_source(tmp_path):
    workspace = tmp_path / "local-study"
    workspace.mkdir()
    source, revision = _local_source(workspace)
    (workspace / "dipl" / "src").mkdir(parents=True)
    model = workspace / "dipl" / "src" / "adapter.py"
    model.write_text("value = 1\n")
    (workspace / "project.json").write_text(json.dumps({
        "id": "test", "source_revision": revision,
        "hub": {"setup_manifest": "projects/test/setups.json"},
    }))
    (workspace / "setups.json").write_text(json.dumps({
        "schema_version": 1, "setups": {"example": {"capability": "native-inputs-only"}},
    }))
    bundle = ProjectBundle.load(workspace)

    def render(context):
        (context.stage / "input.txt").write_text("ready\n")

    output = prepare_setup(bundle, "example", workspace / "runs" / "example",
                           source_root=source, render=render, inputs_only=True)
    lock = json.loads((output / "setup-lock.json").read_text())
    assert lock["source_revision"] == revision
    assert lock["source_dirty"] is False
    assert lock["capability"] == "native-inputs-only"
    assert len(lock["dipl_sha256"]) == 64

    (workspace / ".snthub").mkdir()
    (workspace / ".snthub" / "lock.json").write_text(json.dumps({
        "schema_version": 1, "project": "test", "source_revision": revision,
        "hub_revision": "a" * 40, "dipl_sha256": lock["dipl_sha256"],
    }))
    model.write_text("value = 2\n")
    changed = ProjectBundle.load(workspace)
    changed_output = prepare_setup(changed, "example", workspace / "runs" / "changed",
                                   source_root=source, render=render, inputs_only=True)
    changed_lock = json.loads((changed_output / "setup-lock.json").read_text())
    assert changed_lock["hub_revision"] == "a" * 40
    assert changed_lock["dipl_modified"] is True
    assert changed_lock["dipl_sha256"] != lock["dipl_sha256"]

    baseline = workspace / ".snthub" / "hub" / "projects" / "test" / "dipl" / "src"
    baseline.mkdir(parents=True)
    (baseline / "adapter.py").write_text("value = 1\n")
    workspace_lock = json.loads((workspace / ".snthub" / "lock.json").read_text())
    workspace_lock.pop("dipl_sha256")
    (workspace / ".snthub" / "lock.json").write_text(json.dumps(workspace_lock))
    baseline_bundle = ProjectBundle.load(workspace)
    baseline_output = prepare_setup(baseline_bundle, "example", workspace / "runs" / "baseline",
                                    source_root=source, render=render, inputs_only=True)
    assert json.loads((baseline_output / "setup-lock.json").read_text())["dipl_modified"] is True

    record = json.loads((workspace / "project.json").read_text())
    record["hub"]["setup_manifest"] = "projects/other/setups.json"
    (workspace / "project.json").write_text(json.dumps(record))
    with pytest.raises(HubSetupError, match="Setup manifest"):
        ProjectBundle.load(workspace)
