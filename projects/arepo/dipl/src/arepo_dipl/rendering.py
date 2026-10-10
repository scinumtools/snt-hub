"""Format Arepo native records from an adapter-owned, resolved output plan."""

from typing import Any


class GenerationError(RuntimeError):
    pass


def value_at(env: Any, path: str) -> Any:
    try:
        return env[path].value
    except Exception as exc:
        raise GenerationError(f"Missing active DIPL node `{path}`.") from exc


def format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def render_native(env: Any, outputs: Any, target: str) -> list[str]:
    """Render only active mappings; snapshot replay uses the saved decisions."""
    comment = "#" if target == "config" else "%"
    lines = []
    for item in outputs.select(target, True):
        source = item.source_path
        if source:
            node = env[source]
            description = " ".join(node.metadata.description.splitlines())
            label = f"DIPL {source}" + (f": {description}" if description else ".")
        else:
            label = f"Derived from {', '.join(item.dependencies)}."
        lines.append(f"{comment} {label}")
        if target == "config":
            lines.append(item.key if isinstance(item.value, bool) else
                         f"{item.key}={format_value(item.value)}")
        else:
            lines.append(f"{item.key:<42}{format_value(item.value)}")
    return lines
