"""Unit-aware overrides through the real manifest and native renderer."""

import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).parents[2]
DIP_ROOT = ROOT / "dipl"
SOURCE = DIP_ROOT / "examples/alfven_wave_1d/DIPfile"


def run_override(body):
    """Generate from the bundled setup with an isolated, manifest-owned override."""
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        override = folder / "overrides.dip"
        override.write_text(body)

        def absolute_file(match):
            name = match.group(1)
            path = override if name == "overrides.dip" else (SOURCE.parent / name).resolve()
            return f'file = "{path}"'

        manifest = folder / "DIPfile"
        manifest.write_text(re.sub(r'file = "([^"]+)"', absolute_file, SOURCE.read_text()))
        script = """from pathlib import Path
import sys
from scinumtools3.dip import DIP, Environment
from arepo_dipl.generator import _render_parameters
parser = DIP()
parser.add_project(Path(sys.argv[1]))
env = parser.parse()
text = _render_parameters(env)
Path(sys.argv[2]).write_text(text)
snapshot = Path(sys.argv[3])
env.save(snapshot)
loaded = Environment()
loaded.load(snapshot)
assert _render_parameters(loaded) == text
"""
        output = folder / "param.txt"
        result = subprocess.run(
            [sys.executable, "-B", "-c", script, str(manifest), str(output),
             str(folder / "environment.diph5")],
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                 "PYTHONPATH": f"{DIP_ROOT / 'src'}:{os.environ.get('PYTHONPATH', '')}"},
            capture_output=True, text=True,
        )
        values = {}
        if output.exists():
            for line in output.read_text().splitlines():
                if line and not line.startswith("%"):
                    name, value = line.split()
                    values[name] = value
        return result, values


class OverrideUnitTests(unittest.TestCase):
    def test_time_override_converts_hours_to_native_seconds(self):
        result, values = run_override("resources.wall_clock.limit = 1 h\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(float(values["TimeLimitCPU"]), 3600)

    def test_length_override_converts_metres_to_code_lengths(self):
        result, values = run_override("simulation.domain.box.size = 2 m\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(float(values["BoxSize"]), 200)  # One code length is 1 cm.

    def test_code_unit_override_changes_downstream_length_conversion(self):
        result, values = run_override(
            "code_units.length = 2 cm\nsimulation.domain.box.size = 1 m\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(float(values["UnitLength_in_cm"]), 2)
        self.assertEqual(float(values["BoxSize"]), 50)

    def test_incompatible_override_units_are_rejected(self):
        result, _ = run_override("simulation.domain.box.size = 2 s\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unit", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
