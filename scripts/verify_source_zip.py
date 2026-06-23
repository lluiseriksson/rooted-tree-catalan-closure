#!/usr/bin/env python3
"""Verify a downloaded source ZIP without trusting host permission bits after extraction."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from release_integrity import (
    IntegrityError,
    archive_members,
    parse_source_manifest,
    sha256,
    sha256_file,
    validate_archive_resource_limits,
    validate_zip_info,
)
from source_inventory import source_exclusion_reason
from strict_json import StrictJSONError, loads_canonical as strict_json_loads

PREFIX_RE = re.compile(r"^rooted-tree-catalan-closure-v(\d+\.\d+\.\d+)$")


@dataclass(frozen=True)
class SourceZipReport:
    archive: str
    archive_sha256: str
    prefix: str
    version: str
    release_date: str
    source_file_count: int
    source_file_bytes: int
    source_manifest_sha256: str
    executable_file_count: int


def _parse_checksum(path: Path, archive_name: str) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise IntegrityError(f"cannot read external checksum {path}: {exc}") from exc
    if not text.endswith("\n") or len(text.splitlines()) != 1:
        raise IntegrityError("external checksum must contain exactly one newline-terminated record")
    line = text[:-1]
    try:
        digest, name = line.split("  ", 1)
    except ValueError as exc:
        raise IntegrityError("malformed external checksum record") from exc
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise IntegrityError("external checksum has an invalid SHA-256 digest")
    if name != archive_name:
        raise IntegrityError(f"external checksum names {name!r}, expected {archive_name!r}")
    return digest


def _project_metadata(raw: bytes, source: str) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IntegrityError(f"{source} is not UTF-8: {exc}") from exc
    try:
        project = strict_json_loads(text, source=source)
    except StrictJSONError as exc:
        raise IntegrityError(str(exc)) from exc
    if not isinstance(project, dict):
        raise IntegrityError(f"{source} must contain a JSON object")
    return project


def verify_source_zip(
    archive_path: Path,
    *,
    checksum_path: Path | None = None,
    expected_version: str | None = None,
) -> SourceZipReport:
    """Verify source-archive bytes and return a machine-readable report."""
    archive_path = archive_path.resolve()
    if not archive_path.is_file():
        raise IntegrityError(f"missing source archive: {archive_path}")
    archive_digest = sha256_file(archive_path)
    if checksum_path is not None:
        expected_digest = _parse_checksum(checksum_path.resolve(), archive_path.name)
        if expected_digest != archive_digest:
            raise IntegrityError("external source-archive checksum mismatch")

    try:
        with zipfile.ZipFile(archive_path) as source_zip:
            if source_zip.comment:
                raise IntegrityError("ZIP has a nonempty archive comment")
            infos = source_zip.infolist()
            if not infos:
                raise IntegrityError("source ZIP is empty")
            validate_archive_resource_limits(infos)
            prefixes: set[str] = set()
            for info in infos:
                if "/" not in info.filename:
                    raise IntegrityError(f"ZIP entry has no top-level directory: {info.filename!r}")
                prefix, _ = info.filename.split("/", 1)
                prefixes.add(prefix)
            if len(prefixes) != 1:
                raise IntegrityError(f"ZIP has multiple top-level directories: {sorted(prefixes)}")
            prefix = next(iter(prefixes))
            prefix_match = PREFIX_RE.fullmatch(prefix)
            if prefix_match is None:
                raise IntegrityError(f"unexpected source-archive prefix: {prefix!r}")
            prefix_version = prefix_match.group(1)
            if expected_version is not None and prefix_version != expected_version:
                raise IntegrityError(
                    f"source-archive version {prefix_version} does not match expected {expected_version}"
                )

            members = archive_members(infos, prefix)
            manifest_relative = "SOURCE-MANIFEST.sha256"
            for relative in members:
                if relative == manifest_relative:
                    continue
                exclusion = source_exclusion_reason(relative)
                if exclusion is not None:
                    raise IntegrityError(
                        f"source ZIP contains an excluded path {relative!r}: {exclusion}"
                    )
            if manifest_relative not in members:
                raise IntegrityError("ZIP lacks SOURCE-MANIFEST.sha256")
            if "project.json" not in members:
                raise IntegrityError("ZIP lacks project.json")
            project = _project_metadata(
                source_zip.read(members["project.json"]),
                f"{archive_path.name}:project.json",
            )
            if project.get("name") != "rooted-tree-catalan-closure":
                raise IntegrityError("project.json has an unexpected project name")
            version = project.get("version")
            if version != prefix_version:
                raise IntegrityError("source-archive prefix and project.json version disagree")
            raw_date = project.get("release_date")
            if not isinstance(raw_date, str):
                raise IntegrityError("project.json release_date is not a string")
            try:
                release_date = date.fromisoformat(raw_date)
            except ValueError as exc:
                raise IntegrityError("project.json release_date is invalid") from exc
            expected_timestamp = (
                release_date.year,
                release_date.month,
                release_date.day,
                0,
                0,
                0,
            )

            names = [info.filename for info in infos]
            manifest_name = f"{prefix}/{manifest_relative}"
            expected_order = [
                f"{prefix}/{relative}"
                for relative in sorted(path for path in members if path != manifest_relative)
            ] + [manifest_name]
            if names != expected_order:
                raise IntegrityError("ZIP entries are not in canonical path order")

            executable_count = 0
            for relative, info in members.items():
                mode = validate_zip_info(info, expected_timestamp)
                expected_mode = 0o755 if relative.endswith((".py", ".sh")) else 0o644
                if mode != expected_mode:
                    raise IntegrityError(
                        f"ZIP mode policy mismatch for {relative}: {oct(mode)} != {oct(expected_mode)}"
                    )
                executable_count += mode == 0o755

            manifest_bytes = source_zip.read(members[manifest_relative])
            try:
                manifest_text = manifest_bytes.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise IntegrityError(f"source manifest is not UTF-8: {exc}") from exc
            manifest_records = parse_source_manifest(manifest_text)
            archived_files = {
                relative: info
                for relative, info in members.items()
                if relative != manifest_relative
            }
            if set(archived_files) != set(manifest_records):
                missing = sorted(set(manifest_records) - set(archived_files))
                extra = sorted(set(archived_files) - set(manifest_records))
                raise IntegrityError(
                    f"ZIP contents do not match the source manifest; missing={missing}, extra={extra}"
                )
            source_bytes = 0
            for relative, info in archived_files.items():
                payload = source_zip.read(info)
                source_bytes += len(payload)
                if sha256(payload) != manifest_records[relative]:
                    raise IntegrityError(f"source-manifest checksum mismatch: {relative}")
            bad_crc = source_zip.testzip()
            if bad_crc is not None:
                raise IntegrityError(f"ZIP CRC failure: {bad_crc}")
    except (OSError, zipfile.BadZipFile) as exc:
        raise IntegrityError(f"cannot read source ZIP: {exc}") from exc

    return SourceZipReport(
        archive=archive_path.name,
        archive_sha256=archive_digest,
        prefix=prefix,
        version=prefix_version,
        release_date=raw_date,
        source_file_count=len(manifest_records),
        source_file_bytes=source_bytes,
        source_manifest_sha256=sha256(manifest_bytes),
        executable_file_count=executable_count,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument(
        "--checksum",
        type=Path,
        help="optional external .zip.sha256 sidecar",
    )
    parser.add_argument("--expected-version")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    checksum = args.checksum
    if checksum is None:
        candidate = args.archive.with_name(args.archive.name + ".sha256")
        if candidate.is_file():
            checksum = candidate
    try:
        report = verify_source_zip(
            args.archive,
            checksum_path=checksum,
            expected_version=args.expected_version,
        )
    except IntegrityError as exc:
        if args.as_json:
            print(json.dumps({"error": str(exc), "ok": False}, indent=2, sort_keys=True))
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    payload = {"ok": True, **asdict(report)}
    if args.as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(
            "source ZIP verification passed: "
            f"version={report.version}, files={report.source_file_count}, "
            f"bytes={report.source_file_bytes}, sha256={report.archive_sha256}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
