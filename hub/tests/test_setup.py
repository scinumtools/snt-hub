"""The shared runner must never publish a partial project setup."""

import json

import pytest

from snt_hub_runtime import ProjectBundle, prepare_setup


def test_render_failure_leaves_destination_unpublished(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "project.json").write_text(json.dumps({"id": "test", "source_revision": "0" * 40}))
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
        prepare_setup(bundle, "example", output, source_root=project,
                      render=failing_render, inputs_only=True)

    assert not output.exists()
    assert not list(tmp_path.glob(".test-setup-*"))
