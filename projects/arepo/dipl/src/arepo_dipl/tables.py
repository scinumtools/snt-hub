"""Render imported scientific datasets without changing their numeric conventions."""

from typing import Any

from scinumtools3.dip import inspect_table

from .rendering import GenerationError, value_at


def _array(value: Any) -> list:
    return value if isinstance(value, list) else [value]


def render_tables(env: Any, plan: Any = None) -> dict[str, str]:
    if plan is None:
        from .generator import _outputs
        plan = _outputs(env)
    outputs: dict[str, str] = {}
    for mapping in plan.select("dataset", True):
        dataset = mapping.key
        filename = mapping.value
        if filename in outputs:
            raise GenerationError(f"Duplicate dataset output `{filename}`.")
        table = inspect_table(env, dataset + ".data")
        values = [_array(value_at(env, column.path)) for column in table.columns]
        if not values or len({len(column) for column in values}) != 1:
            raise GenerationError(f"Dataset `{dataset}` has missing or unequal-length columns.")
        preamble = env.select("?" + dataset + ".preamble")
        lines = [preamble[0].value] if preamble else []
        # Seventeen significant digits preserve binary64 values on reload.
        lines.extend(" ".join(f"{value:.17g}" for value in row) for row in zip(*values))
        outputs[filename] = "\n".join(lines) + "\n"
    return outputs
