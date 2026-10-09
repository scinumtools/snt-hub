"""Evaluate one bundled DIPL project with an optional per-run override."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any


def evaluate_project(manifest: Path, override_file: Path | None = None,
                     *, dip_factory: Callable[[], Any] | None = None) -> Any:
    if dip_factory is None:
        from scinumtools3.dip import DIP

        dip_factory = DIP
    dip = dip_factory()
    dip.add_project(manifest)
    if override_file is not None:
        dip.add_override_file(Path(override_file).resolve())
    return dip.parse()
