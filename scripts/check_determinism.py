#!/usr/bin/env python3
"""Build release outputs twice and require every output byte to be identical."""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def snapshot(directory: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(directory.iterdir()) if path.is_file()}


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="rtc-release-a-") as first, tempfile.TemporaryDirectory(
        prefix="rtc-release-b-"
    ) as second:
        for directory in (first, second):
            subprocess.run(
                [sys.executable, "scripts/package_release.py", "--output-dir", directory],
                cwd=ROOT,
                check=True,
            )
            subprocess.run(
                [sys.executable, "scripts/verify_release.py", "--release-dir", directory],
                cwd=ROOT,
                check=True,
            )
        left = snapshot(Path(first))
        right = snapshot(Path(second))
        if left.keys() != right.keys():
            raise SystemExit("release determinism failed: output file sets differ")
        mismatched = [name for name in left if left[name] != right[name]]
        if mismatched:
            raise SystemExit("release determinism failed: byte differences in " + ", ".join(mismatched))
        print("release determinism passed: " + ", ".join(left))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
