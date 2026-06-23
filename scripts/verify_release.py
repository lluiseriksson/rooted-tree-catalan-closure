#!/usr/bin/env python3
"""Independently verify release bytes, inventories, metadata, and source parity."""

from __future__ import annotations

import argparse
import hashlib
import json
import stat
import sys
import zipfile
from datetime import datetime
from pathlib import Path

from package_release import ROOT, file_license, repository_files


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", default="release")
    args = parser.parse_args()

    project = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
    prefix = f"rooted-tree-catalan-closure-v{project['version']}"
    release = Path(args.release_dir)
    if not release.is_absolute():
        release = ROOT / release
    release = release.resolve()
    archive = release / f"{prefix}.zip"
    checksum = release / f"{prefix}.zip.sha256"
    sbom_path = release / f"{prefix}.spdx.json"
    meta_path = release / f"{prefix}.release.json"
    for path in (archive, checksum, sbom_path, meta_path):
        if not path.is_file():
            fail(f"missing release file: {path}")

    digest = sha256(archive.read_bytes())
    expected_line = f"{digest}  {archive.name}"
    if checksum.read_text(encoding="utf-8").strip() != expected_line:
        fail("external archive checksum mismatch")

    release_date = datetime.fromisoformat(project["release_date"])
    expected_timestamp = (release_date.year, release_date.month, release_date.day, 0, 0, 0)
    manifest_name = f"{prefix}/SOURCE-MANIFEST.sha256"
    with zipfile.ZipFile(archive) as source_zip:
        if source_zip.comment:
            fail("ZIP has a nonempty archive comment")
        infos = source_zip.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            fail("ZIP contains duplicate names")
        if any(name.startswith("/") or ".." in Path(name).parts for name in names):
            fail("ZIP contains an unsafe path")
        if manifest_name not in names:
            fail("ZIP lacks the internal source manifest")
        expected_order = sorted(name for name in names if name != manifest_name) + [manifest_name]
        if names != expected_order:
            fail("ZIP entries are not in canonical path order")
        for info in infos:
            if info.compress_type != zipfile.ZIP_STORED:
                fail(f"ZIP entry is compressed and may vary across zlib versions: {info.filename}")
            if info.date_time != expected_timestamp:
                fail(f"ZIP timestamp drift: {info.filename}: {info.date_time}")
            if info.create_system != 3:
                fail(f"ZIP entry is not normalized as Unix: {info.filename}")
            mode = stat.S_IMODE(info.external_attr >> 16)
            if mode not in {0o644, 0o755}:
                fail(f"unexpected ZIP mode {oct(mode)}: {info.filename}")
            if info.extra:
                fail(f"ZIP entry contains noncanonical extra metadata: {info.filename}")
        manifest_bytes = source_zip.read(manifest_name)
        manifest = manifest_bytes.decode("utf-8")
        manifest_records: dict[str, str] = {}
        for line in manifest.splitlines():
            digest_value, rel = line.split("  ", 1)
            if rel in manifest_records:
                fail(f"duplicate path in internal manifest: {rel}")
            manifest_records[rel] = digest_value
        archived_files = {
            name[len(prefix) + 1 :]: name for name in names if name != manifest_name
        }
        if set(archived_files) != set(manifest_records):
            fail("ZIP contents do not match internal manifest paths")
        for rel, name in archived_files.items():
            if sha256(source_zip.read(name)) != manifest_records[rel]:
                fail(f"internal manifest checksum mismatch: {rel}")

    current_records = {
        path.relative_to(ROOT).as_posix(): sha256(path.read_bytes())
        for path in repository_files(release)
    }
    if current_records != manifest_records:
        missing = sorted(set(current_records) - set(manifest_records))
        extra = sorted(set(manifest_records) - set(current_records))
        changed = sorted(
            rel
            for rel in set(current_records) & set(manifest_records)
            if current_records[rel] != manifest_records[rel]
        )
        fail(f"release/source parity failed; missing={missing}, extra={extra}, changed={changed}")

    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    sbom_records = {
        entry["fileName"].removeprefix("./"): entry["checksums"][0]["checksumValue"]
        for entry in sbom["files"]
    }
    if sbom_records != manifest_records:
        fail("SPDX file inventory does not match source manifest")
    for entry in sbom["files"]:
        rel = entry["fileName"].removeprefix("./")
        expected_license = file_license(rel)
        if entry["licenseConcluded"] != expected_license:
            fail(f"SPDX license mismatch for {rel}")
    if sbom["packages"][0]["licenseDeclared"] != "AGPL-3.0-or-later AND CC-BY-4.0":
        fail("SPDX package license expression drift")

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    if meta.get("schema_version") != 2:
        fail("unsupported release metadata schema")
    if meta["source_archive"] != archive.name or meta["source_archive_sha256"] != digest:
        fail("release metadata does not match source archive")
    if meta["source_tree_sha256"] != sha256(manifest_bytes):
        fail("release metadata source-tree checksum mismatch")
    if meta["source_file_count"] != len(manifest_records):
        fail("release metadata source-file count mismatch")
    if meta["archive_method"] != "ZIP_STORED":
        fail("release metadata archive method mismatch")
    if meta["version"] != project["version"] or meta["formal_status"] != project["status"]:
        fail("release metadata does not match project metadata")
    history = meta.get("history_backup", {})
    if history.get("outputs") != project["history_backup_outputs"]:
        fail("release metadata history-output inventory mismatch")
    if history.get("byte_reproducibility_claim") is not False:
        fail("release metadata overclaims Git-bundle byte reproducibility")
    for key, rel in (
        ("finite_evidence", "evidence/finite-catalan-checks.json"),
        ("theorem_manifest", "archive/theorem-manifest.json"),
    ):
        if meta[key]["path"] != rel or meta[key]["sha256"] != current_records[rel]:
            fail(f"release metadata mismatch for {key}")

    print(
        f"release verification passed: {len(manifest_records)} source files, "
        f"cross-runtime stored ZIP, sha256 {digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
