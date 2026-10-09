"""Discover tagged values and apply their optional typed export settings."""

from dataclasses import dataclass, field
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


@dataclass
class ExportPolicy:
    enabled: bool = True
    omit_nonpositive: bool = False
    requires_enabled: list[str] = field(default_factory=list)

    @classmethod
    def read(cls, env: Any, path: str) -> "ExportPolicy":
        prefix = path + ".export."
        fields = {}
        for setting in env.select("?" + prefix):
            name = setting.name.removeprefix(prefix)
            value = setting.value
            if name == "requires_enabled":
                # SNT unwraps singleton arrays in the Python value accessor.
                if list(setting.shape) == [1]:
                    value = [value]
                valid = len(setting.shape) == 1 and isinstance(value, list) and all(
                    isinstance(item, str) and item for item in value)
            elif name in ("enabled", "omit_nonpositive"):
                valid = list(setting.shape) == [1] and isinstance(value, bool)
            else:
                raise GenerationError(f"Unknown export setting `{setting.name}`.")
            if not valid:
                raise GenerationError(f"Invalid type or value for export setting `{setting.name}`.")
            fields[name] = value
        return cls(**fields)

    def active(self, env: Any) -> bool:
        if not self.enabled:
            return False
        enabled = True
        for path in self.requires_enabled:
            value = value_at(env, path)
            if not isinstance(value, bool):
                raise GenerationError(f"Export dependency `{path}` must be a boolean feature.")
            enabled = enabled and value
        return enabled


def render_native(env: Any, target: str) -> list[str]:
    """Discover exports in stable path order and apply their declared policy.

    `?requires` remains descriptive metadata: it is not an export predicate.
    Tags only identify output targets. Policy is read from typed child nodes.
    """
    comment = "#" if target == "config" else "%"
    lines: list[str] = []
    emitted: dict[str, str] = {}
    for node in sorted(env.select("?", tags_all=[f"arepo:{target}"]), key=lambda item: item.name):
        for tag in node.tags:
            if tag.startswith("arepo:") and tag not in ("arepo:config", "arepo:param"):
                raise GenerationError(f"Unknown export tag `{tag}` on `{node.name}`; use an export child for policy.")
        policy = ExportPolicy.read(env, node.name)
        if not policy.active(env):
            continue
        value = node.value
        flag = target == "config" and isinstance(value, bool)
        if flag and not value:
            continue
        if policy.omit_nonpositive and float(value) <= 0:
            continue
        names = node.metadata.native
        if not names:
            raise GenerationError(f"Exported node `{node.name}` has no `?native` metadata.")
        for native in names:
            if native in emitted:
                raise GenerationError(
                    f"Duplicate native name `{native}` from `{emitted[native]}` and `{node.name}`."
                )
            emitted[native] = node.name
            description = " ".join(node.metadata.description.splitlines())
            lines.append(f"{comment} DIPL {node.name}" + (f": {description}" if description else "."))
            if target == "config":
                lines.append(native if flag else f"{native}={format_value(value)}")
            else:
                lines.append(f"{native:<42}{format_value(value)}")
    return lines
