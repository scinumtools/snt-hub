"""The schema export cache must follow shared DIPL inputs and the SNT binary."""

import json
import subprocess

from scripts import generate_schema_hierarchies as generator


def test_schema_exports_rebuild_only_for_changed_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(generator, "ROOT", tmp_path)
    project = tmp_path / "projects" / "sample"
    shared = project / "dipl" / "profiles" / "shared.dip"
    shared.parent.mkdir(parents=True)
    shared.write_text("value = 1\n")
    for name, content in (("one", 'file = "../../profiles/shared.dip"\n'),
                          ("two", 'file = "local.dip"\n')):
        directory = project / "dipl" / "examples" / name
        directory.mkdir(parents=True)
        (directory / "DIPfile").write_text(content)
        if name == "two":
            (directory / "local.dip").write_text("value = 2\n")

    executable = tmp_path / "snt"
    executable.write_bytes(b"snt version one")
    monkeypatch.setattr(generator, "snt_executable", lambda _: executable)
    calls = []

    def export(command, **_kwargs):
        calls.append(command[command.index("--project") + 1])
        return subprocess.CompletedProcess(command, 0, json.dumps({
            "schema": "snt-schema-hierarchy/1", "definitions_available": True,
        }))

    monkeypatch.setattr(generator.subprocess, "run", export)
    names = ["one", "two"]
    assert generator.generate("sample", names, "snt") == (2, 0)
    assert generator.generate("sample", names, "snt") == (0, 2)
    assert len(calls) == 2

    shared.write_text("value = 3\n")
    assert generator.generate("sample", names, "snt") == (1, 1)
    assert calls[-1].endswith("/one/DIPfile")

    output = project / "docs" / "schemas" / "two.json"
    output.write_text("corrupted\n")
    assert generator.generate("sample", names, "snt") == (1, 1)
    assert calls[-1].endswith("/two/DIPfile")

    executable.write_bytes(b"snt version two")
    assert generator.generate("sample", names, "snt") == (2, 0)
