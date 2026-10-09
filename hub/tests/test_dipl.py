from snt_hub_runtime.dipl import evaluate_project


def test_project_and_override_are_registered_before_parsing(tmp_path):
    calls = []

    class FakeDIP:
        def add_project(self, path):
            calls.append(("project", path))

        def add_override_file(self, path):
            calls.append(("override", path))

        def parse(self):
            calls.append(("parse",))
            return "environment"

    manifest = tmp_path / "DIPfile"
    override = tmp_path / "override.dip"
    assert evaluate_project(manifest, override, dip_factory=FakeDIP) == "environment"
    assert calls == [("project", manifest), ("override", override.resolve()), ("parse",)]
    calls.clear()
    evaluate_project(manifest, dip_factory=FakeDIP)
    assert calls == [("project", manifest), ("parse",)]
