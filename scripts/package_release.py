#!/usr/bin/env python3
"""Create deterministic source ZIP, checksum, SPDX 2.3 SBOM, and metadata."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {'.git', 'release', 'build', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache'}
EXCLUDED_SUFFIXES = {'.aux', '.fdb_latexmk', '.fls', '.log.tmp', '.out', '.synctex.gz', '.toc'}
EXCLUDED_NAMES = {'main.pdf'}

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def repository_files(output_dir: Path) -> list[Path]:
    try:
        raw = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT, stderr=subprocess.DEVNULL)
        candidates = [ROOT / item.decode('utf-8') for item in raw.split(b'\0') if item]
    except (FileNotFoundError, subprocess.CalledProcessError):
        candidates = [p for p in ROOT.rglob('*') if p.is_file()]
    selected: list[Path] = []
    for path in candidates:
        if not path.is_file() or path.is_symlink():
            continue
        try:
            path.resolve().relative_to(output_dir)
        except ValueError:
            pass
        else:
            continue
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        if path.name in EXCLUDED_NAMES or any(path.name.endswith(s) for s in EXCLUDED_SUFFIXES):
            continue
        selected.append(path)
    return sorted(selected, key=lambda p: p.relative_to(ROOT).as_posix())

def zip_info(name: str, timestamp: tuple[int, int, int, int, int, int], executable: bool = False) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=timestamp)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = ((0o755 if executable else 0o644) & 0xFFFF) << 16
    info.flag_bits |= 0x800
    return info

def spdx_id(path: str) -> str:
    return 'SPDXRef-File-' + ''.join(c if c.isalnum() or c in '.-' else '-' for c in path)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', default='release')
    args = parser.parse_args()
    project = json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))
    version = project['version']
    release_date = datetime.fromisoformat(project['release_date']).replace(tzinfo=timezone.utc)
    timestamp = (release_date.year, release_date.month, release_date.day, 0, 0, 0)
    prefix = f"rooted-tree-catalan-closure-v{version}"
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / f'{prefix}.zip'
    checksum_path = output_dir / f'{prefix}.zip.sha256'
    sbom_path = output_dir / f'{prefix}.spdx.json'
    metadata_path = output_dir / f'{prefix}.release.json'

    files = repository_files(output_dir)
    records = []
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        data = path.read_bytes()
        records.append({'path': rel, 'size': len(data), 'sha256': sha256(data)})
    manifest = ''.join(f"{r['sha256']}  {r['path']}\n" for r in records).encode('utf-8')
    with zipfile.ZipFile(zip_path, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path, record in zip(files, records, strict=True):
            rel = str(record['path'])
            executable = os.access(path, os.X_OK) or rel.endswith(('.sh', '.py'))
            zf.writestr(zip_info(f'{prefix}/{rel}', timestamp, executable), path.read_bytes())
        zf.writestr(zip_info(f'{prefix}/SOURCE-MANIFEST.sha256', timestamp), manifest)

    zip_digest = sha256(zip_path.read_bytes())
    checksum_path.write_text(f'{zip_digest}  {zip_path.name}\n', encoding='utf-8', newline='\n')
    namespace_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"{project['repository']}@v{version}")
    package_id = 'SPDXRef-Package'
    spdx_files = []
    relationships = [{'spdxElementId': 'SPDXRef-DOCUMENT', 'relationshipType': 'DESCRIBES', 'relatedSpdxElement': package_id}]
    for record in records:
        rel = str(record['path'])
        file_id = spdx_id(rel)
        spdx_files.append({'SPDXID': file_id, 'fileName': f'./{rel}',
            'checksums': [{'algorithm': 'SHA256', 'checksumValue': record['sha256']}],
            'licenseConcluded': 'NOASSERTION', 'licenseInfoInFiles': ['NOASSERTION'],
            'copyrightText': 'NOASSERTION'})
        relationships.append({'spdxElementId': package_id, 'relationshipType': 'CONTAINS', 'relatedSpdxElement': file_id})
    sbom = {'spdxVersion': 'SPDX-2.3', 'dataLicense': 'CC0-1.0', 'SPDXID': 'SPDXRef-DOCUMENT',
        'name': f'{prefix}-source', 'documentNamespace': f'https://spdx.org/spdxdocs/{prefix}-{namespace_uuid}',
        'creationInfo': {'created': release_date.strftime('%Y-%m-%dT00:00:00Z'),
            'creators': ['Tool: rooted-tree-catalan-closure/scripts/package_release.py']},
        'packages': [{'name': project['name'], 'SPDXID': package_id, 'versionInfo': version,
            'downloadLocation': project['repository'], 'filesAnalyzed': True,
            'licenseConcluded': 'NOASSERTION', 'licenseDeclared': 'NOASSERTION',
            'copyrightText': 'Copyright (c) 2026 Lluis Eriksson'}],
        'files': spdx_files, 'relationships': relationships}
    sbom_path.write_text(json.dumps(sbom, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    release_meta = {'schema_version': 1, 'name': project['name'], 'version': version,
        'release_date': project['release_date'], 'source_archive': zip_path.name,
        'source_archive_sha256': zip_digest, 'source_file_count': len(records),
        'source_manifest': 'SOURCE-MANIFEST.sha256', 'sbom': sbom_path.name,
        'formal_status': project['status'], 'unresolved_obligation': project['unresolved_obligation'],
        'upstream': project['upstream']}
    metadata_path.write_text(json.dumps(release_meta, indent=2, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
    for path in (zip_path, checksum_path, sbom_path, metadata_path):
        print(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
