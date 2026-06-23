#!/usr/bin/env python3
"""Independently verify release bytes, inventories, metadata, and source parity."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import uuid
import zipfile
from datetime import datetime
from pathlib import Path

from package_release import (
    ARCHIVED_EVIDENCE_LOGS,
    ROOT,
    file_license,
    repository_files,
    spdx_id,
)
from release_integrity import (
    MAX_ARCHIVE_FILES,
    MAX_ARCHIVE_FILE_BYTES,
    MAX_ARCHIVE_TOTAL_BYTES,
    IntegrityError,
    archive_members,
    parse_source_manifest,
    portable_path_key,
    safe_extract_members,
    sha256,
    validate_archive_resource_limits,
    validate_portable_relative_path,
    validate_zip_info,
)
from strict_json import StrictJSONError, load as load_json
from verify_source_zip import verify_source_zip


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def load_object(path: Path, label: str) -> dict[str, object]:
    try:
        value = load_json(path)
    except StrictJSONError as exc:
        fail(str(exc))
    if not isinstance(value, dict):
        fail(f"{label} must contain a JSON object")
    return value


def run_extracted_self_audit(extracted_root: Path) -> None:
    command = [sys.executable, "scripts/check_repository.py"]
    proc = subprocess.run(
        command,
        cwd=extracted_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        fail(
            "extracted source archive failed its repository audit:\n"
            + proc.stdout
            + proc.stderr
        )


def sbom_file_records(sbom: dict[str, object]) -> dict[str, str]:
    """Return a strict SPDX path/checksum map without silent duplicate overwrites."""
    entries = sbom.get("files")
    if not isinstance(entries, list):
        raise IntegrityError("SPDX document has no file inventory")
    records: dict[str, str] = {}
    folded: dict[str, str] = {}
    for index, raw_entry in enumerate(entries, 1):
        if not isinstance(raw_entry, dict):
            raise IntegrityError(f"SPDX file entry {index} is not an object")
        raw_name = raw_entry.get("fileName")
        if not isinstance(raw_name, str) or not raw_name.startswith("./"):
            raise IntegrityError(f"SPDX file entry {index} has a noncanonical fileName")
        relative = validate_portable_relative_path(raw_name[2:])
        if relative in records:
            raise IntegrityError(f"duplicate SPDX file path: {relative}")
        folded_key = portable_path_key(relative)
        previous = folded.get(folded_key)
        if previous is not None and previous != relative:
            raise IntegrityError(f"case-insensitive SPDX path collision: {previous!r} and {relative!r}")
        checksums = raw_entry.get("checksums")
        if not isinstance(checksums, list) or len(checksums) != 1 or not isinstance(checksums[0], dict):
            raise IntegrityError(f"SPDX file entry {relative} must have exactly one checksum")
        checksum = checksums[0]
        if checksum.get("algorithm") != "SHA256" or not isinstance(checksum.get("checksumValue"), str):
            raise IntegrityError(f"SPDX file entry {relative} lacks a SHA256 checksum")
        digest = str(checksum["checksumValue"])
        if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise IntegrityError(f"SPDX file entry {relative} has an invalid SHA256 checksum")
        if raw_entry.get("SPDXID") != spdx_id(relative):
            raise IntegrityError(f"SPDX file entry {relative} has a noncanonical SPDXID")
        records[relative] = digest
        folded[folded_key] = relative
    if list(records) != sorted(records):
        raise IntegrityError("SPDX file inventory is not in canonical path order")
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", default="release")
    args = parser.parse_args()

    project = load_object(ROOT / "project.json", "project.json")
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

    try:
        standalone_report = verify_source_zip(
            archive, checksum_path=checksum, expected_version=str(project["version"])
        )
    except IntegrityError as exc:
        fail(f"standalone source-ZIP verification failed: {exc}")
    digest = standalone_report.archive_sha256

    release_date = datetime.fromisoformat(project["release_date"])
    expected_timestamp = (release_date.year, release_date.month, release_date.day, 0, 0, 0)
    manifest_relative = "SOURCE-MANIFEST.sha256"
    manifest_name = f"{prefix}/{manifest_relative}"

    with tempfile.TemporaryDirectory(prefix="rtcc-source-audit-") as temp:
        extraction_root = Path(temp)
        try:
            with zipfile.ZipFile(archive) as source_zip:
                if source_zip.comment:
                    raise IntegrityError("ZIP has a nonempty archive comment")
                infos = source_zip.infolist()
                validate_archive_resource_limits(infos)
                members = archive_members(infos, prefix)
                if manifest_relative not in members:
                    raise IntegrityError("ZIP lacks the internal source manifest")
                names = [info.filename for info in infos]
                expected_order = [
                    f"{prefix}/{relative}"
                    for relative in sorted(path for path in members if path != manifest_relative)
                ] + [manifest_name]
                if names != expected_order:
                    raise IntegrityError("ZIP entries are not in canonical path order")
                for info in infos:
                    validate_zip_info(info, expected_timestamp)

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
                        f"ZIP contents do not match internal manifest paths; missing={missing}, extra={extra}"
                    )
                for relative, info in archived_files.items():
                    if sha256(source_zip.read(info)) != manifest_records[relative]:
                        raise IntegrityError(f"internal manifest checksum mismatch: {relative}")
                for relative in ARCHIVED_EVIDENCE_LOGS:
                    if relative not in archived_files:
                        raise IntegrityError(f"source ZIP omits archived verification evidence: {relative}")
                extracted_root = safe_extract_members(source_zip, members, extraction_root, prefix)
        except (OSError, zipfile.BadZipFile, IntegrityError) as exc:
            fail(str(exc))

        if not extracted_root.is_dir():
            fail("source ZIP does not have the expected single top-level directory")
        run_extracted_self_audit(extracted_root)

    current_records = {
        path.relative_to(ROOT).as_posix(): sha256(path.read_bytes())
        for path in repository_files(release)
    }
    if standalone_report.source_file_count != len(manifest_records):
        fail("standalone source-ZIP report file count drift")
    if standalone_report.source_manifest_sha256 != sha256(manifest_bytes):
        fail("standalone source-ZIP report manifest digest drift")

    if current_records != manifest_records:
        missing = sorted(set(current_records) - set(manifest_records))
        extra = sorted(set(manifest_records) - set(current_records))
        changed = sorted(
            relative
            for relative in set(current_records) & set(manifest_records)
            if current_records[relative] != manifest_records[relative]
        )
        fail(f"release/source parity failed; missing={missing}, extra={extra}, changed={changed}")

    sbom = load_object(sbom_path, "SPDX document")
    try:
        sbom_records = sbom_file_records(sbom)
    except IntegrityError as exc:
        fail(str(exc))
    if sbom_records != manifest_records:
        fail("SPDX file inventory does not match source manifest")
    if sbom.get("spdxVersion") != "SPDX-2.3" or sbom.get("dataLicense") != "CC0-1.0":
        fail("SPDX document header drift")
    namespace_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"{project['repository']}@v{project['version']}")
    expected_namespace = f"https://spdx.org/spdxdocs/{prefix}-{namespace_uuid}"
    if sbom.get("documentNamespace") != expected_namespace:
        fail("SPDX document namespace drift")
    creation = sbom.get("creationInfo", {})
    if creation.get("created") != release_date.strftime("%Y-%m-%dT00:00:00Z"):
        fail("SPDX creation timestamp drift")
    packages = sbom.get("packages")
    if not isinstance(packages, list) or len(packages) != 1 or not isinstance(packages[0], dict):
        fail("SPDX package inventory drift")
    package = packages[0]
    if package.get("SPDXID") != "SPDXRef-Package" or package.get("versionInfo") != project["version"]:
        fail("SPDX package identity/version drift")
    if package.get("downloadLocation") != project["repository"] or package.get("filesAnalyzed") is not True:
        fail("SPDX package source metadata drift")
    if package.get("licenseDeclared") != "AGPL-3.0-or-later AND CC-BY-4.0":
        fail("SPDX package license expression drift")
    package_checksums = package.get("checksums")
    if package_checksums != [{"algorithm": "SHA256", "checksumValue": sha256(manifest_bytes)}]:
        fail("SPDX package source-tree checksum drift")
    file_ids: set[str] = set()
    for entry in sbom["files"]:
        relative = entry["fileName"].removeprefix("./")
        expected_license = file_license(relative)
        if entry["licenseConcluded"] != expected_license:
            fail(f"SPDX license mismatch for {relative}")
        if entry.get("licenseInfoInFiles") != [expected_license]:
            fail(f"SPDX licenseInfoInFiles mismatch for {relative}")
        file_id = entry["SPDXID"]
        if file_id in file_ids:
            fail(f"duplicate SPDX identifier: {file_id}")
        file_ids.add(file_id)
    expected_relationships = {
        ("SPDXRef-DOCUMENT", "DESCRIBES", "SPDXRef-Package"),
        *(("SPDXRef-Package", "CONTAINS", file_id) for file_id in file_ids),
    }
    relationships = sbom.get("relationships")
    if not isinstance(relationships, list):
        fail("SPDX relationship inventory is missing")
    actual_relationships: set[tuple[str, str, str]] = set()
    for relation in relationships:
        if not isinstance(relation, dict):
            fail("SPDX relationship entry is not an object")
        actual_relationships.add(
            (
                str(relation.get("spdxElementId")),
                str(relation.get("relationshipType")),
                str(relation.get("relatedSpdxElement")),
            )
        )
    if len(actual_relationships) != len(relationships) or actual_relationships != expected_relationships:
        fail("SPDX relationship inventory drift")

    meta = load_object(meta_path, "release metadata")
    if meta.get("schema_version") != 4:
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
    self_audit = meta.get("source_archive_self_audit", {})
    if self_audit.get("required") is not True:
        fail("release metadata does not require source-archive self-audit")
    if self_audit.get("command") != "python scripts/check_repository.py":
        fail("release metadata source-archive audit command drift")
    if self_audit.get("manifest_command") != "python scripts/check_source_manifest.py":
        fail("release metadata source-manifest command drift")
    expected_standalone = (
        f"python scripts/verify_source_zip.py {archive.name} --checksum {checksum.name}"
    )
    if self_audit.get("standalone_zip_command") != expected_standalone:
        fail("release metadata standalone source-ZIP command drift")
    if self_audit.get("host_extracted_modes_authoritative") is not False:
        fail("release metadata incorrectly trusts host-extracted permission bits")
    expected_limits = {
        "max_files": MAX_ARCHIVE_FILES,
        "max_file_bytes": MAX_ARCHIVE_FILE_BYTES,
        "max_total_bytes": MAX_ARCHIVE_TOTAL_BYTES,
    }
    if self_audit.get("resource_limits") != expected_limits:
        fail("release metadata source-archive resource limits drift")
    if self_audit.get("archived_evidence_logs") != list(ARCHIVED_EVIDENCE_LOGS):
        fail("release metadata archived-evidence inventory drift")
    if self_audit.get("repackaging_verified") is not True:
        fail("release metadata does not record extracted-source repackaging support")
    history = meta.get("history_backup", {})
    if history.get("outputs") != project["history_backup_outputs"]:
        fail("release metadata history-output inventory mismatch")
    if history.get("inventory_schema") != 2:
        fail("release metadata history inventory schema drift")
    if history.get("exact_bundle_heads_verified") is not True:
        fail("release metadata does not require exact Git bundle head verification")
    if history.get("byte_reproducibility_claim") is not False:
        fail("release metadata overclaims Git-bundle byte reproducibility")
    for key, relative in (
        ("finite_evidence", "evidence/finite-catalan-checks.json"),
        ("theorem_manifest", "archive/theorem-manifest.json"),
    ):
        if meta[key]["path"] != relative or meta[key]["sha256"] != current_records[relative]:
            fail(f"release metadata mismatch for {key}")

    print(
        f"release verification passed: {len(manifest_records)} source files, "
        f"portable self-auditing cross-runtime stored ZIP, sha256 {digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
