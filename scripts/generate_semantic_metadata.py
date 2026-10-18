"""Generate SNT3 json-metadata exports without changing existing project reports."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def render(snt: str, dipfile: Path) -> str:
    with tempfile.TemporaryDirectory(prefix="snt-hub-metadata-") as directory:
        output = Path(directory) / "metadata.json"
        subprocess.run(
            [snt, "dip", "parse", "--project", str(dipfile.relative_to(ROOT)),
             "--generate", "json-metadata", str(output)],
            cwd=ROOT, check=True,
        )
        document = json.loads(output.read_text())
    if (document.get("schema") != "snt-dip-values/2"
            or not isinstance(document.get("values"), dict)
            or not isinstance(document.get("node_metadata"), dict)
            or not isinstance(document.get("sources"), dict)):
        raise ValueError(f"Unexpected SNT3 metadata contract: {dipfile}")
    for source in document["sources"].values():
        path = source.get("path", "")
        if path and Path(path).is_absolute():
            source["path"] = str(Path(path).resolve().relative_to(ROOT))
    return json.dumps(document, ensure_ascii=False, separators=(",", ":")) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Generate only one project")
    parser.add_argument("--check", action="store_true", help="Check exports without writing")
    parser.add_argument("--snt", default="snt", help="SNT3 executable")
    args = parser.parse_args()
    snt = shutil.which(args.snt)
    if not snt:
        parser.error(f"SNT3 executable not found: {args.snt}")
    projects = sorted((ROOT / "projects").glob("*/project.json"))
    if args.project:
        projects = [path for path in projects if path.parent.name == args.project]
        if not projects:
            parser.error(f"Unknown project: {args.project}")
    stale = []
    for record in projects:
        project = record.parent
        setups = json.loads((project / "setups.json").read_text())["setups"]
        for setup in sorted(setups):
            dipfile = project / "dipl" / "examples" / setup / "DIPfile"
            target = project / "docs" / "semantic" / f"{setup}.json"
            content = render(snt, dipfile)
            if target.is_file() and target.read_text() == content:
                continue
            if args.check:
                stale.append(target.relative_to(ROOT))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
                print(f"generated {target.relative_to(ROOT)}", flush=True)
    if stale:
        print("Stale semantic metadata exports:\n" + "\n".join(map(str, stale)), file=sys.stderr)
        return 1
    print(f"Checked semantic metadata for {len(projects)} projects.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
