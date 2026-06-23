#!/usr/bin/env python3
"""Verify an extracted source release against its internal SHA-256 manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from release_integrity import IntegrityError, compare_manifest_to_files, parse_source_manifest
from source_inventory import repository_files

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_NAME = "SOURCE-MANIFEST.sha256"


def audit_source_manifest(root: Path, *, required: bool = True) -> list[str]:
    """Return source-manifest diagnostics for ``root``."""
    root = root.resolve()
    manifest_path = root / MANIFEST_NAME
    if not manifest_path.is_file():
        return [f"missing {MANIFEST_NAME}"] if required else []
    try:
        manifest = parse_source_manifest(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, IntegrityError) as exc:
        return [f"invalid {MANIFEST_NAME}: {exc}"]
    files = repository_files(root, root / "release")
    return compare_manifest_to_files(manifest, root, files)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--if-present",
        action="store_true",
        help="succeed when the manifest is absent, as in a normal Git checkout",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    errors = audit_source_manifest(args.root, required=not args.if_present)
    if args.as_json:
        print(json.dumps({"errors": errors, "ok": not errors}, indent=2, sort_keys=True))
    else:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if not errors:
            print("source manifest verification passed")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
