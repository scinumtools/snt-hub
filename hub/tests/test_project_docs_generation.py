"""The project document cache follows shared DIPL inputs and the SNT binary."""

import json
import subprocess
from pathlib import Path

from scripts import generate_project_docs as generator


def test_schema_exports_rebuild_only_for_changed_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(generator, "ROOT", tmp_path)
    project = tmp_path / "projects" / "sample"
    project.mkdir(parents=True)
    (project / "project.json").write_text(json.dumps({"name": "Sample", "reviewed_on": "2026-01-01"}))
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
    monkeypatch.setattr(generator, "executable_path", lambda _: executable)
    calls = []

    def export(command, **_kwargs):
        calls.append(command[1])
        if command[1] == "report":
            report_path = command[command.index("--output") + 1]
            Path(report_path).write_text(json.dumps({"schema": "briefpp/1"}))
            return subprocess.CompletedProcess(command, 0)
        return subprocess.CompletedProcess(command, 0, json.dumps({
            "schema": "snt-schema-hierarchy/1", "definitions_available": True,
        }))

    monkeypatch.setattr(generator.subprocess, "run", export)
    names = ["one", "two"]
    assert generator.generate(project, names, "snt", False, False) == (2, 0, [])
    assert generator.generate(project, names, "snt", False, False) == (0, 2, [])
    assert len(calls) == 4

    shared.write_text("value = 3\n")
    assert generator.generate(project, names, "snt", False, False) == (0, 2, [])
    assert calls.count("report") == 3
    assert calls.count("dip") == 3

    output = project / "docs" / "schemas" / "two.json"
    output.write_text("corrupted\n")
    assert generator.generate(project, names, "snt", False, False) == (1, 1, [])
    assert output.read_text().startswith('{"schema":"snt-schema-hierarchy/1"')

    executable.write_bytes(b"snt version two")
    assert generator.generate(project, names, "snt", False, False) == (0, 2, [])
