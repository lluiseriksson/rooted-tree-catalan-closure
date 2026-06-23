#!/usr/bin/env python3
"""Independently verify generated release artifacts and their cross-references."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def fail(message: str) -> None:
    print(f'ERROR: {message}', file=sys.stderr)
    raise SystemExit(1)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--release-dir', default='release')
    args = parser.parse_args()
    project = json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))
    prefix = f"rooted-tree-catalan-closure-v{project['version']}"
    release = Path(args.release_dir)
    if not release.is_absolute():
        release = ROOT / release
    archive = release / f'{prefix}.zip'
    checksum = release / f'{prefix}.zip.sha256'
    sbom_path = release / f'{prefix}.spdx.json'
    meta_path = release / f'{prefix}.release.json'
    for path in (archive, checksum, sbom_path, meta_path):
        if not path.is_file():
            fail(f'missing release file: {path}')
    digest = sha256(archive.read_bytes())
    expected_line = f'{digest}  {archive.name}'
    if checksum.read_text(encoding='utf-8').strip() != expected_line:
        fail('external archive checksum mismatch')
    with zipfile.ZipFile(archive) as zf:
        names = zf.namelist()
        if len(names) != len(set(names)):
            fail('ZIP contains duplicate names')
        if any(name.startswith('/') or '..' in Path(name).parts for name in names):
            fail('ZIP contains unsafe path')
        manifest_name = f'{prefix}/SOURCE-MANIFEST.sha256'
        if manifest_name not in names:
            fail('ZIP lacks internal source manifest')
        manifest = zf.read(manifest_name).decode('utf-8')
        manifest_records: dict[str, str] = {}
        for line in manifest.splitlines():
            digest_value, rel = line.split('  ', 1)
            manifest_records[rel] = digest_value
        archived_files = {name[len(prefix)+1:]: name for name in names if name != manifest_name}
        if set(archived_files) != set(manifest_records):
            fail('ZIP contents do not match internal manifest paths')
        for rel, name in archived_files.items():
            if sha256(zf.read(name)) != manifest_records[rel]:
                fail(f'internal manifest checksum mismatch: {rel}')
    sbom = json.loads(sbom_path.read_text(encoding='utf-8'))
    sbom_records = {entry['fileName'].removeprefix('./'): entry['checksums'][0]['checksumValue'] for entry in sbom['files']}
    if sbom_records != manifest_records:
        fail('SPDX file inventory does not match source manifest')
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    if meta['source_archive'] != archive.name or meta['source_archive_sha256'] != digest:
        fail('release metadata does not match source archive')
    if meta['version'] != project['version'] or meta['formal_status'] != project['status']:
        fail('release metadata does not match project metadata')
    print(f'release verification passed: {len(manifest_records)} source files, sha256 {digest}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
