"""Read saved adapter mappings as the value interface used by native renderers."""

from __future__ import annotations

from typing import Any


class PlannedValues:
    """Expose recorded node values without consulting the live DIPL environment."""

    def __init__(self, outputs: Any) -> None:
        self._mappings = {mapping.source_path: mapping for mapping in outputs.mappings
                          if mapping.source_path}

    def __getitem__(self, path: str) -> Any:
        return self._mappings[path]

    def active(self, path: str) -> bool:
        return self._mappings[path].active
