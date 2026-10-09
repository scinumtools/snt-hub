"""Behavioral coverage for tag-driven exports and the catalog migration."""

import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from scinumtools3.dip import DIP, Environment
from arepo_dipl.rendering import GenerationError, render_native


ROOT = Path(__file__).parents[1]


def parse(source):
    parser = DIP()
    parser.add_file(ROOT / "profiles" / "schemas" / "export.dip")
    parser.add_string(source)
    return parser.parse()


def entries(env, target):
    return [line for line in render_native(env, target) if not line.startswith(("#", "%"))]


class RenderingTests(unittest.TestCase):
    def test_manifest_loads_unwrapped_overrides_before_dependencies(self):
        from arepo_dipl.generator import load_environment

        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            folder = Path(directory)
            manifest = folder / "DIPfile"
            manifest.write_text('code[]\n  file = "profile.dip"\noverrides[]\n  file = "tuning.dip"\n')
            (folder / "profile.dip").write_text('''$schema time_settings
  initial_redshift float = 127
simulation.time : time_settings
simulation.time.begin float = ( 1 / ( 1 + {?simulation.time.initial_redshift} ) )
''')
            overrides = folder / "tuning.dip"
            with patch.dict("arepo_dipl.generator.SETUPS", {"host_test": manifest}):
                for body in ("", "# No tuning\n"):
                    overrides.write_text(body)
                    env = load_environment("host_test")
                    self.assertEqual(env["simulation.time.begin"].value, 1 / 128)
                overrides.write_text("simulation\n  time\n    initial_redshift = 63\n")
                env = load_environment("host_test")
                self.assertEqual(env["simulation.time.begin"].value, 1 / 64)
                self.assertTrue(env.select("?simulation.time.initial_redshift")[0].override)
                snapshot = folder / "environment.diph5"
                env.save(snapshot)
                loaded = Environment()
                loaded.load(snapshot)
                self.assertEqual(loaded["simulation.time.begin"].value, 1 / 64)
                self.assertTrue(loaded.select("?simulation.time.initial_redshift")[0].override)
                self.assertIn("63", loaded["simulation.time.initial_redshift"].provenance.override_code)
                overrides.write_text("simulation.time.nonexistent = 63\n")
                with self.assertRaises(RuntimeError):
                    load_environment("host_test")

    def test_discovery_schema_override_and_persistence(self):
        env = parse('''$schema controls
  enabled bool = false
    !tags ["arepo:config"]
    ?native ["FEATURE", "SECOND_FEATURE"]
  speed float = 100 cm/s
    !tags ["arepo:param"]
    ?native "Speed"
  disabled bool = false
    !tags ["arepo:config"]
    ?native "DISABLED"
  runtime_switch bool = false
    !tags ["arepo:param"]
    ?native "RuntimeSwitch"
settings : controls
  enabled = true
  speed = 3 m/s
unexported int = 99
  ?native "NotExported"
''')
        # A previously unknown schema needs no Python registration.
        self.assertEqual(entries(env, "config"), ["FEATURE", "SECOND_FEATURE"])
        self.assertEqual([line.split() for line in entries(env, "param")],
                         [["RuntimeSwitch", "0"], ["Speed", "300"]])
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "environment.diph5"
            env.save(path)
            loaded = Environment()
            loaded.load(path)
            for target in ("config", "param"):
                self.assertEqual(render_native(env, target), render_native(loaded, target))

    def test_feature_dependencies_and_positive_values(self):
        env = parse('''feature bool = false
second_feature bool = true
zero int = 0
  !tags ["arepo:config"]
  ?native "ZERO"
  export : arepo_export
    omit_nonpositive = true
active int = 2
  !tags ["arepo:config"]
  ?native "ACTIVE"
  export : arepo_export
    omit_nonpositive = true
gated int = 3
  !tags ["arepo:param"]
  ?native "Gated"
  export : arepo_export
    requires_enabled = ["feature", "second_feature"]
chosen int = 4
  !tags ["arepo:param"]
  ?native "Chosen"
  export : arepo_export
    requires_enabled = ["second_feature"]
other int = 5
  !tags ["arepo:param"]
  ?native "Other"
  export : arepo_export
    enabled = false
''')
        self.assertEqual(entries(env, "config"), ["ACTIVE=2"])
        self.assertEqual([line.split() for line in entries(env, "param")], [["Chosen", "4"]])

    def test_export_errors_are_actionable(self):
        cases = [
            ('x int = 1\n  !tags ["arepo:param"]\n', "has no `?native`"),
            ('x int = 1\n  !tags ["arepo:param", "arepo:gate:feature"]\n', "Unknown export tag"),
            ('x int = 1\n  !tags ["arepo:param"]\n  export : arepo_export\n'
             '    requires_enabled = ["missing"]\n', "Missing active DIPL node"),
            ('feature int = 1\nx int = 1\n  !tags ["arepo:param"]\n'
             '  export : arepo_export\n    requires_enabled = ["feature"]\n', "must be a boolean feature"),
            ('x int = 1\n  !tags ["arepo:param"]\n  export\n    untis str = "cm"\n', "Unknown export setting"),
            ('x int = 1\n  !tags ["arepo:param"]\n  export\n    enabled str = "yes"\n', "Invalid type"),
            ('x int = 1\n  !tags ["arepo:param"]\n  ?native "Same"\n'
             'y int = 2\n  !tags ["arepo:param"]\n  ?native "Same"\n', "Duplicate native name"),
        ]
        for source, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(GenerationError, re.escape(message)):
                entries(parse(source), "param")

    def test_policy_and_feature_overrides_are_applied_at_export(self):
        env = parse('''feature bool = false
x float = 200 cm
  !tags ["arepo:param"]
  ?native "Length"
  export : arepo_export
    requires_enabled = ["feature"]
    enabled = false
feature = true
x.export.enabled = true
x = 2 m
''')
        self.assertEqual([line.split() for line in entries(env, "param")], [["Length", "200"]])

    def test_derived_controls_follow_overrides(self):
        parser = DIP()
        parser.add_string('''simulation.time.coordinate str = "linear"
simulation.domain.boundary str = "non_periodic"
build.physics.cooling bool = false
build.physics.star_formation bool = false
''')
        parser.add_string('build.physics.cooling = true\nsimulation.time.coordinate = "scale_factor"\n')
        parser.add_file(ROOT / "profiles" / "native_controls.dip")
        self.assertEqual(dict(line.split() for line in entries(parser.parse(), "param")), {
            "ComovingIntegrationOn": "1", "PeriodicBoundariesOn": "0",
            "CoolingOn": "1", "StarformationOn": "0",
        })

    def test_all_setups_roundtrip_native_outputs_and_tables(self):
        from arepo_dipl.generator import SETUPS

        script = '''import json, sys, tempfile
from pathlib import Path
from scinumtools3.dip import Environment
from arepo_dipl.generator import generate, _render_config, _render_parameters, _render_schedule
from arepo_dipl.tables import render_tables
with tempfile.TemporaryDirectory(dir=sys.argv[2]) as directory:
    path = generate(Path(directory), sys.argv[1])
    outputs = {name: (path / name).read_text() for name in ("Config.sh", "param.txt")}
    env = Environment()
    env.load(path / "environment.diph5")
    if env["output.schedule.enabled"].value:
        outputs["output_list.txt"] = (path / env["output.schedule.filename"].value).read_text()
    else:
        assert not (path / "output_list.txt").exists()
        outputs["output_list.txt"] = ""
    assert _render_config(env) == outputs["Config.sh"]
    assert _render_parameters(env) == outputs["param.txt"]
    assert _render_schedule(env) == outputs["output_list.txt"]
    datasets = render_tables(env)
    inventory = json.loads((Path(sys.argv[2]) / "tests/table_inventory.json").read_text())
    for record in inventory:
        if record["setup"] != sys.argv[1]:
            continue
        filename = record["filename"]
        rendered = (path / filename).read_text()
        # Cooling's declared path has an explicit ./ prefix.
        assert rendered == datasets.get(filename, datasets.get("./" + filename))
        original = (Path(sys.argv[2]).parent / "source" / record["source"]).read_text()
        def numeric_rows(text):
            return [[float(item) for item in line.split()] for line in text.splitlines()
                    if line.strip() and not line.lstrip().startswith("#")]
        assert numeric_rows(rendered) == numeric_rows(original), record["source"]
    print(json.dumps(outputs))
'''
        # Different setups redefine the same custom units, so isolate their
        # process-global PUEL registrations, as separate CLI invocations do.
        for setup in SETUPS:
            with self.subTest(setup=setup):
                outputs = json.loads(subprocess.check_output(
                    [sys.executable, "-B", "-c", script, setup, str(ROOT)], text=True))
                schedules = {
                    "cosmo_zoom_gravity_only_3d": [.0197, .2, .25, .33, .5, .66, 1],
                    "galaxy_merger_star_formation_3d": [3*i/31 for i in range(32)],
                    "isolated_galaxy_collisionless_3d": [i/9 for i in range(10)],
                }
                if setup in schedules:
                    rows = [line.split() for line in outputs["output_list.txt"].splitlines()]
                    self.assertEqual([float(row[0]) for row in rows],
                                     [float(f"{time:g}") for time in schedules[setup]])
                    self.assertEqual([int(row[1]) for row in rows], [1]*len(rows))

    def test_regeneration_preserves_existing_build(self):
        from arepo_dipl.generator import generate

        env = parse('output.schedule.enabled bool = false\n'
                    'gravity.softenings.particle_type_map int[:] = []\n')
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "generated"
            with patch("arepo_dipl.generator.load_environment", return_value=env):
                generate(output)
                (output / "Arepo").write_text("compiled")
                (output / "param.txt").write_text("stale")
                generate(output)
            self.assertEqual((output / "Arepo").read_text(), "compiled")
            self.assertNotEqual((output / "param.txt").read_text(), "stale")
            loaded = Environment()
            loaded.load(output / "environment.diph5")
            self.assertFalse(loaded["output.schedule.enabled"].value)

    def test_enabled_schedule_requires_matching_table(self):
        from arepo_dipl.generator import _render_schedule

        with self.assertRaisesRegex(GenerationError, "output_schedule.time"):
            _render_schedule(parse('output.schedule.enabled bool = true\n'
                                   'simulation.time.coordinate str = "linear"\n'))
        self.assertEqual(_render_schedule(parse('output.schedule.enabled bool = false\n')), "")

    def test_schedule_output_uses_configured_filename(self):
        from arepo_dipl.generator import generate

        source = '''output.schedule.enabled bool = true
output.schedule.filename str = "./schedules/custom.txt"
  !tags ["arepo:param"]
  ?native "OutputListFilename"
simulation.time.coordinate str = "linear"
gravity.softenings.particle_type_map int[:] = []
output_schedule table = """
time float
write_flag int
---
0.25 1
0.5 1
"""
'''
        env = parse(source)
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "generated"
            with patch("arepo_dipl.generator.load_environment", return_value=env):
                generate(output)
            self.assertEqual((output / "schedules/custom.txt").read_text(), "0.25 1\n0.5 1\n")
            self.assertIn("./schedules/custom.txt", (output / "param.txt").read_text())
            self.assertFalse((output / "output_list.txt").exists())

        for filename in ("../outside.txt", "param.txt", "environment.diph5", "Config.sh", "."):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory(dir=ROOT) as directory:
                output = Path(directory) / "generated"
                env = parse(source.replace("./schedules/custom.txt", filename))
                with patch("arepo_dipl.generator.load_environment", return_value=env):
                    with self.assertRaisesRegex(RuntimeError, "output path|conflicts"):
                        generate(output)
                self.assertFalse(output.exists())

        dataset = '''datasets.reference
  output_file str = "schedules/custom.txt"
    !tags ["arepo:dataset"]
  data table = """
x float
---
1
2
"""
'''
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            env = parse(source + dataset)
            with patch("arepo_dipl.generator.load_environment", return_value=env):
                with self.assertRaisesRegex(RuntimeError, "conflicts"):
                    generate(Path(directory) / "generated")

    def test_all_supplied_numeric_tables_are_in_inventory(self):
        supplied = {"data/TREECOOL_ep"}
        source_root = ROOT.parent / "source"
        for path in (source_root / "examples").rglob("*"):
            if not path.is_file() or path.suffix not in (".txt", ".dat"):
                continue
            try:
                rows = [[float(value) for value in line.split()] for line in path.read_text().splitlines()
                        if line.strip() and not line.lstrip().startswith("#")]
            except (UnicodeError, ValueError):
                continue  # Parameter files and binary initial conditions are not numeric tables.
            if rows:
                supplied.add(str(path.relative_to(source_root)))
        inventory = json.loads((ROOT / "tests/table_inventory.json").read_text())
        self.assertEqual({record["source"] for record in inventory}, supplied)


if __name__ == "__main__":
    unittest.main()
