"""Compare generated native settings directly with the bundled Arepo examples."""

import ast
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

from arepo_dipl.generator import SETUPS


ROOT = Path(__file__).parents[2]
DIP_ROOT = ROOT / "dipl"
SOURCE_ROOT = ROOT / "source"
EXAMPLE_NAMES = {
    "cosmological_gravity_only": "cosmo_box_gravity_only_3d",
    "cosmological_star_formation": "cosmo_box_star_formation_3d",
    "mhd_shock_tube": "mhd_shocktube_1d",
}


def settings(path):
    """Read active Config.sh or param.txt entries, rejecting duplicate names."""
    config = path.name == "Config.sh"
    marker = "#" if config else "%"
    result = {}
    for number, source in enumerate(path.read_text().splitlines(), 1):
        line = source.split(marker, 1)[0].split(";", 1)[0].strip()
        if not line:
            continue
        if config:
            name, separator, value = line.partition("=")
            name = name.strip()
            value = value.strip() if separator else None
        else:
            parts = line.split()
            if len(parts) != 2:
                raise AssertionError(f"{path}:{number}: expected name and value: {line!r}")
            name, value = parts
        if name in result:
            raise AssertionError(f"{path}:{number}: duplicate setting {name}")
        result[name] = value
    return result


def number(value):
    """Evaluate numeric literals and simple arithmetic used in bundled configs."""
    def evaluate(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            operand = evaluate(node.operand)
            return operand if isinstance(node.op, ast.UAdd) else -operand
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left, right = evaluate(node.left), evaluate(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            return left / right
        raise ValueError(value)

    try:
        return evaluate(ast.parse(value, mode="eval").body)
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError):
        return None


def test_bundled_examples_are_covered():
    originals = {path.parent.name for path in (SOURCE_ROOT / "examples").glob("*/Config.sh")
                 if (path.parent / "param.txt").is_file()}
    assert originals == {EXAMPLE_NAMES.get(name, name) for name in SETUPS}


@pytest.mark.parametrize("setup", sorted(SETUPS))
def test_generated_settings_match_bundled_example(setup):
    # Custom unit names are registered process-wide by SciNumTools, so each
    # setup gets a fresh interpreter, like a normal CLI invocation.
    script = """from pathlib import Path
import sys
from arepo_dipl.generator import generate
from scinumtools3.dip import Environment
output = generate(Path(sys.argv[2]), sys.argv[1])
env = Environment()
env.load(output / "environment.diph5")
print(env["build.gravity.softening_types"].value)
"""
    with tempfile.TemporaryDirectory() as directory:
        process = subprocess.run(
            [sys.executable, "-B", "-c", script, setup, directory],
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1",
                 "PYTHONPATH": f"{DIP_ROOT / 'src'}:{os.environ.get('PYTHONPATH', '')}"},
            capture_output=True, text=True,
        )
        assert process.returncode == 0, f"{setup}: {process.stderr}"
        declared_softening_types = int(process.stdout.strip())
        original = SOURCE_ROOT / "examples" / EXAMPLE_NAMES.get(setup, setup)
        generated = Path(directory)
        config = settings(generated / "Config.sh")
        params = settings(generated / "param.txt")
        native_softening_types = int(config.get("NSOFTTYPES") or 6)
        assert declared_softening_types == native_softening_types, setup
        for prefix in ("SofteningComovingType", "SofteningMaxPhysType"):
            assert {name for name in params if name.startswith(prefix)} == {
                f"{prefix}{index}" for index in range(declared_softening_types)
            }, f"{setup}: {prefix} family count"
        for filename in ("Config.sh", "param.txt"):
            expected = settings(original / filename)
            actual = settings(generated / filename)
            assert set(expected) == set(actual), (
                f"{setup}/{filename}: missing {sorted(set(expected) - set(actual))}; "
                f"extra {sorted(set(actual) - set(expected))}"
            )
            for name, wanted in expected.items():
                found = actual[name]
                if wanted is None:
                    assert found is None, f"{setup}/{filename}: {name}"
                else:
                    wanted_number, found_number = number(wanted), number(found)
                    if wanted_number is not None and found_number is not None:
                        assert math.isclose(wanted_number, found_number,
                                            rel_tol=1e-11, abs_tol=1e-12), (
                            f"{setup}/{filename}: {name}: {found} != {wanted}"
                        )
                    else:
                        assert wanted == found, f"{setup}/{filename}: {name}"
