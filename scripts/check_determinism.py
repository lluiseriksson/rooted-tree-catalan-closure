#!/usr/bin/env python3
"""Build release outputs twice and require byte-identical results."""
from __future__ import annotations

import filecmp
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def snapshot(directory: Path) -> dict[str, bytes]:
    return {p.name: p.read_bytes() for p in sorted(directory.iterdir()) if p.is_file()}

def main() -> int:
    with tempfile.TemporaryDirectory(prefix='rtc-release-a-') as a, tempfile.TemporaryDirectory(prefix='rtc-release-b-') as b:
        for directory in (a, b):
            subprocess.run([sys.executable, 'scripts/package_release.py', '--output-dir', directory], cwd=ROOT, check=True)
        left, right = snapshot(Path(a)), snapshot(Path(b))
        if left.keys() != right.keys():
            raise SystemExit('release determinism failed: output file sets differ')
        mismatched = [name for name in left if left[name] != right[name]]
        if mismatched:
            raise SystemExit('release determinism failed: byte differences in ' + ', '.join(mismatched))
        print('release determinism passed: ' + ', '.join(left))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
