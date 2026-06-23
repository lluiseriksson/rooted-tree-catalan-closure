#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'release'
ZIP_NAME = 'rooted-tree-catalan-closure-source.zip'
EXCLUDE_PARTS = {'.git', '.lake', 'build', 'release', '__pycache__', '.pytest_cache'}
EXCLUDE_SUFFIXES = {'.aux', '.log', '.out', '.toc', '.fls', '.fdb_latexmk', '.synctex.gz'}

def include(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if any(part in EXCLUDE_PARTS for part in rel.parts):
        return False
    if path.name == 'main.pdf':
        return False
    if any(str(path).endswith(s) for s in EXCLUDE_SUFFIXES):
        return False
    return path.is_file()

def main() -> None:
    RELEASE.mkdir(exist_ok=True)
    zip_path = RELEASE / ZIP_NAME
    files = sorted(p for p in ROOT.rglob('*') if include(p))
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in files:
            info = zipfile.ZipInfo(str(p.relative_to(ROOT)))
            info.date_time = (2026, 6, 23, 0, 0, 0)
            info.external_attr = 0o644 << 16
            zf.writestr(info, p.read_bytes())
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    (RELEASE / f'{ZIP_NAME}.sha256').write_text(f'{digest}  {ZIP_NAME}\n', encoding='utf-8')
    print(f'wrote {zip_path}')
    print(digest)

if __name__ == '__main__':
    main()
