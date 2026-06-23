#!/usr/bin/env python3
from __future__ import annotations

import shutil
import sys
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / 'files'

def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('usage: python apply_improvements.py /path/to/rooted-tree-catalan-closure')
    target = Path(sys.argv[1]).resolve()
    if not (target / '.git').exists():
        raise SystemExit(f'{target} does not look like a git checkout')
    for src in SOURCE.rglob('*'):
        if src.is_file():
            rel = src.relative_to(SOURCE)
            dst = target / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f'wrote {rel}')

if __name__ == '__main__':
    main()
