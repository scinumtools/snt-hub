"""Read-only coverage inventory for the untouched Arepo source tree."""

from __future__ import annotations

import re
from pathlib import Path


def template_flags(root: Path) -> set[str]:
    flags: set[str] = set()
    for line in (root / "Template-Config.sh").read_text().splitlines():
        body = line.strip()
        if not body or body.startswith("#!/"):
            continue
        # Template-Config.sh documents inactive options as `#FLAG` and
        # `#FLAG=value`; headings begin with `# ` and deliberately do not match.
        match = re.match(r"^#?([A-Z][A-Z0-9_]+)(?:=|\s|$)", body)
        if match:
            flags.add(match.group(1))
    return flags


def runtime_tags(root: Path) -> set[str]:
    text = (root / "src/io/parameters.c").read_text()
    return set(re.findall(r'strcpy\(tag\[nt\],\s*"([A-Za-z0-9_]+)"\)', text))
