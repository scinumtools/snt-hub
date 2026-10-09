"""Smoke checks for the maintainer-facing shell entry point."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).parents[2]
SCRIPT = ROOT / "dipl/setup.sh"


class SetupScriptTests(unittest.TestCase):
    def test_generation_from_another_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "outputs"
            result = subprocess.run(
                [str(SCRIPT), "-g", "alfven_wave_1d"], cwd=directory,
                env={**os.environ, "PYTHON": sys.executable,
                     "DIP_OUTPUT_ROOT": "outputs"},
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            for filename in ("Config.sh", "param.txt", "environment.diph5"):
                self.assertTrue((output / "alfven_wave_1d" / filename).is_file())

    def test_compile_uses_generated_config_and_isolated_build_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            output = folder / "outputs" / "alfven_wave_1d"
            mock_bin = folder / "bin"
            mock_bin.mkdir()
            make = mock_bin / "make"
            make.write_text('''#!/usr/bin/env bash
printf '%s\\n' "$@" > "$MAKE_ARGS_FILE"
printf 'SYSTYPE=%s\\n' "$SYSTYPE" >> "$MAKE_ARGS_FILE"
for arg in "$@"; do
  case "$arg" in EXEC=*) touch "${arg#EXEC=}" ;; esac
done
''')
            make.chmod(0o755)
            arguments = folder / "make-args.txt"
            result = subprocess.run(
                [str(SCRIPT), "-c", "alfven_wave_1d"], cwd=directory,
                env={**os.environ, "PYTHON": sys.executable,
                     "DIP_OUTPUT_ROOT": str(output.parent),
                     "SYSTYPE": "TestSystem", "MAKE_ARGS_FILE": str(arguments),
                     "PATH": f"{mock_bin}:{os.environ['PATH']}"},
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((output / "Config.sh").is_file())
            self.assertTrue((output / "param.txt").is_file())
            self.assertTrue((output / "Arepo").is_file())
            self.assertEqual(set(arguments.read_text().splitlines()), {
                f"CONFIG={output / 'Config.sh'}",
                f"BUILD_DIR={output / 'build'}",
                f"EXEC={output / 'Arepo'}",
                f"PYTHON={sys.executable}",
                "SYSTYPE=TestSystem",
            })


if __name__ == "__main__":
    unittest.main()
