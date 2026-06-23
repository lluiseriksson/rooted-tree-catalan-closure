#!/usr/bin/env python3
"""Independently verify release bytes, inventories, metadata, SBOM, and source parity."""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
import uuid
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Iterable

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
from source_inventory import SourceInventoryError
from strict_json import StrictJSONError, load as load_json
from verify_source_zip import verify_source_zip

SHA1_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


def sha1(data: bytes) -> str:
    """Return SHA-1 solely for mandatory SPDX 2.3 compatibility checks."""
    return hashlib.sha1(data).hexdigest()  # noqa: S324 - required by SPDX 2.3


def spdx_package_verification_code(file_sha1s: Iterable[str]) -> str:
    """Independently compute the SPDX 2.3 package verification code."""
    ordered = sorted(file_sha1s)
    if any(SHA1_RE.fullmatch(digest) is None for digest in ordered):
        raise IntegrityError("invalid SHA-1 digest in SPDX package verification input")
    return sha1("".join(ordered).encode("ascii"))


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


def verify_release_checksum_inventory(
    sums_path: Path,
    expected_paths: Iterable[Path],
) -> dict[str, str]:
    """Verify the canonical complete-release SHA-256 inventory."""
    expected = {path.name: path for path in expected_paths}
    try:
        text = sums_path.read_text(encoding="utf-8")
        records = parse_source_manifest(text)
    except (OSError, UnicodeDecodeError, IntegrityError) as exc:
        raise IntegrityError(f"invalid complete-release checksum inventory: {exc}") from exc
    if set(records) != set(expected):
        missing = sorted(set(expected) - set(records))
        extra = sorted(set(records) - set(expected))
        raise IntegrityError(
            f"complete-release checksum inventory mismatch; missing={missing}, extra={extra}"
        )
    for name, path in expected.items():
        if not path.is_file():
            raise IntegrityError(f"release checksum target is missing: {path}")
        actual = sha256(path.read_bytes())
        if records[name] != actual:
            raise IntegrityError(f"complete-release checksum mismatch: {name}")
    return records


def sbom_file_records(sbom: dict[str, object]) -> dict[str, dict[str, str]]:
    """Return strict SPDX path/SHA1/SHA256 records without duplicate overwrites."""
    entries = sbom.get("files")
    if not isinstance(entries, list):
        raise IntegrityError("SPDX document has no file inventory")
    records: dict[str, dict[str, str]] = {}
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
            raise IntegrityError(
                f"case-insensitive SPDX path collision: {previous!r} and {relative!r}"
            )
        checksums = raw_entry.get("checksums")
        if not isinstance(checksums, list) or len(checksums) != 2:
            raise IntegrityError(
                f"SPDX file entry {relative} must contain canonical SHA1 and SHA256 checksums"
            )
        parsed: dict[str, str] = {}
        for checksum in checksums:
            if not isinstance(checksum, dict) or set(checksum) != {"algorithm", "checksumValue"}:
                raise IntegrityError(f"SPDX file entry {relative} has a malformed checksum")
            algorithm = checksum.get("algorithm")
            value = checksum.get("checksumValue")
            if algorithm not in {"SHA1", "SHA256"} or not isinstance(value, str):
                raise IntegrityError(f"SPDX file entry {relative} has an unsupported checksum")
            if algorithm in parsed:
                raise IntegrityError(
                    f"SPDX file entry {relative} repeats checksum algorithm {algorithm}"
                )
            parsed[algorithm] = value
        if [entry.get("algorithm") for entry in checksums] != ["SHA1", "SHA256"]:
            raise IntegrityError(f"SPDX file entry {relative} checksum order is not canonical")
        if SHA1_RE.fullmatch(parsed.get("SHA1", "")) is None:
            raise IntegrityError(f"SPDX file entry {relative} has an invalid SHA1 checksum")
        if SHA256_RE.fullmatch(parsed.get("SHA256", "")) is None:
            raise IntegrityError(f"SPDX file entry {relative} has an invalid SHA256 checksum")
        if raw_entry.get("SPDXID") != spdx_id(relative):
            raise IntegrityError(f"SPDX file entry {relative} has a noncanonical SPDXID")
        records[relative] = parsed
        folded[folded_key] = relative
    if list(records) != sorted(records):
        raise IntegrityError("SPDX file inventory is not in canonical path order")
    return records


def _project_release_outputs(project: dict[str, object]) -> set[str]:
    outputs = project.get("release_outputs")
    if not isinstance(outputs, list) or not all(isinstance(item, str) for item in outputs):
        raise IntegrityError("project release output inventory is malformed")
    version = str(project["version"])
    return {item.replace("{version}", version) for item in outputs}


def validate_release_output_directory(directory: Path, expected_names: set[str]) -> None:
    """Require one exact set of regular, non-symbolic-link release outputs."""
    if not directory.is_dir():
        raise IntegrityError(f"release directory is missing: {directory}")
    entries = list(directory.iterdir())
    irregular = sorted(
        path.name for path in entries if path.is_symlink() or not path.is_file()
    )
    if irregular:
        raise IntegrityError(
            f"release directory contains non-regular output entries: {irregular}"
        )
    actual_names = {path.name for path in entries}
    if actual_names != expected_names:
        missing = sorted(expected_names - actual_names)
        extra = sorted(actual_names - expected_names)
        raise IntegrityError(
            f"release directory output inventory mismatch; missing={missing}, extra={extra}"
        )


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
    sums_path = release / f"{prefix}.SHA256SUMS"
    release_files = [archive, checksum, sbom_path, meta_path]
    all_release_files = [*release_files, sums_path]

    try:
        expected_output_names = _project_release_outputs(project)
    except IntegrityError as exc:
        fail(str(exc))
    if expected_output_names != {path.name for path in all_release_files}:
        fail("project release output inventory does not match verifier expectations")
    try:
        validate_release_output_directory(release, expected_output_names)
    except IntegrityError as exc:
        fail(str(exc))
    try:
        checksum_records = verify_release_checksum_inventory(sums_path, release_files)
    except IntegrityError as exc:
        fail(str(exc))

    try:
        standalone_report = verify_source_zip(
            archive, checksum_path=checksum, expected_version=str(project["version"])
        )
    except IntegrityError as exc:
        fail(f"standalone source-ZIP verification failed: {exc}")
    digest = standalone_report.archive_sha256
    if checksum_records.get(archive.name) != digest:
        fail("complete-release checksums disagree with standalone ZIP digest")

    raw_release_date = project.get("release_date")
    if not isinstance(raw_release_date, str):
        fail("project release_date is not a string")
    try:
        parsed_release_date = date.fromisoformat(raw_release_date)
    except ValueError:
        fail("project release_date is not an ISO date")
    release_date = datetime(
        parsed_release_date.year,
        parsed_release_date.month,
        parsed_release_date.day,
    )
    expected_timestamp = (release_date.year, release_date.month, release_date.day, 0, 0, 0)
    manifest_relative = "SOURCE-MANIFEST.sha256"
    manifest_name = f"{prefix}/{manifest_relative}"

    archived_sha1: dict[str, str] = {}
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
                        f"ZIP contents do not match internal manifest paths; "
                        f"missing={missing}, extra={extra}"
                    )
                for relative, info in archived_files.items():
                    payload = source_zip.read(info)
                    if sha256(payload) != manifest_records[relative]:
                        raise IntegrityError(f"internal manifest checksum mismatch: {relative}")
                    archived_sha1[relative] = sha1(payload)
                for relative in ARCHIVED_EVIDENCE_LOGS:
                    if relative not in archived_files:
                        raise IntegrityError(
                            f"source ZIP omits archived verification evidence: {relative}"
                        )
                extracted_root = safe_extract_members(
                    source_zip, members, extraction_root, prefix
                )
        except (OSError, zipfile.BadZipFile, IntegrityError) as exc:
            fail(str(exc))

        if not extracted_root.is_dir():
            fail("source ZIP does not have the expected single top-level directory")
        run_extracted_self_audit(extracted_root)

    try:
        current_files = repository_files(release)
    except SourceInventoryError as exc:
        fail(str(exc))
    current_sha256 = {
        path.relative_to(ROOT).as_posix(): sha256(path.read_bytes())
        for path in current_files
    }
    current_sha1 = {
        path.relative_to(ROOT).as_posix(): sha1(path.read_bytes())
        for path in current_files
    }
    if standalone_report.source_file_count != len(manifest_records):
        fail("standalone source-ZIP report file count drift")
    if standalone_report.source_manifest_sha256 != sha256(manifest_bytes):
        fail("standalone source-ZIP report manifest digest drift")

    if current_sha256 != manifest_records:
        missing = sorted(set(current_sha256) - set(manifest_records))
        extra = sorted(set(manifest_records) - set(current_sha256))
        changed = sorted(
            relative
            for relative in set(current_sha256) & set(manifest_records)
            if current_sha256[relative] != manifest_records[relative]
        )
        fail(f"release/source parity failed; missing={missing}, extra={extra}, changed={changed}")
    if current_sha1 != archived_sha1:
        fail("release/source SHA1 parity failed for SPDX verification inputs")

    sbom = load_object(sbom_path, "SPDX document")
    try:
        spdx_records = sbom_file_records(sbom)
    except IntegrityError as exc:
        fail(str(exc))
    sbom_sha256 = {path: values["SHA256"] for path, values in spdx_records.items()}
    sbom_sha1 = {path: values["SHA1"] for path, values in spdx_records.items()}
    if sbom_sha256 != manifest_records:
        fail("SPDX SHA256 file inventory does not match source manifest")
    if sbom_sha1 != archived_sha1:
        fail("SPDX SHA1 file inventory does not match source archive")
    if sbom.get("spdxVersion") != "SPDX-2.3" or sbom.get("dataLicense") != "CC0-1.0":
        fail("SPDX document header drift")
    if sbom.get("documentDescribes") != ["SPDXRef-Package"]:
        fail("SPDX documentDescribes drift")
    namespace_uuid = uuid.uuid5(
        uuid.NAMESPACE_URL, f"{project['repository']}@v{project['version']}"
    )
    expected_namespace = f"https://spdx.org/spdxdocs/{prefix}-{namespace_uuid}"
    if sbom.get("documentNamespace") != expected_namespace:
        fail("SPDX document namespace drift")
    creation = sbom.get("creationInfo", {})
    if not isinstance(creation, dict) or creation.get("created") != release_date.strftime(
        "%Y-%m-%dT00:00:00Z"
    ):
        fail("SPDX creation timestamp drift")
    packages = sbom.get("packages")
    if not isinstance(packages, list) or len(packages) != 1 or not isinstance(packages[0], dict):
        fail("SPDX package inventory drift")
    package = packages[0]
    if package.get("SPDXID") != "SPDXRef-Package" or package.get("versionInfo") != project["version"]:
        fail("SPDX package identity/version drift")
    if package.get("downloadLocation") != project["repository"] or package.get("filesAnalyzed") is not True:
        fail("SPDX package source metadata drift")
    if package.get("packageFileName") != archive.name:
        fail("SPDX package filename drift")
    if package.get("primaryPackagePurpose") != "SOURCE":
        fail("SPDX package purpose drift")
    if package.get("releaseDate") != release_date.strftime("%Y-%m-%dT00:00:00Z"):
        fail("SPDX package release date drift")
    if package.get("licenseDeclared") != "AGPL-3.0-or-later AND CC-BY-4.0":
        fail("SPDX package license expression drift")
    if package.get("licenseConcluded") != "NOASSERTION":
        fail("SPDX package concluded license drift")
    if package.get("licenseInfoFromFiles") != ["NOASSERTION"]:
        fail("SPDX package licenseInfoFromFiles drift")
    if package.get("copyrightText") != "NOASSERTION":
        fail("SPDX package copyright assertion drift")
    package_checksums = package.get("checksums")
    if package_checksums != [{"algorithm": "SHA256", "checksumValue": digest}]:
        fail("SPDX package archive checksum drift")
    expected_verification_code = spdx_package_verification_code(sbom_sha1.values())
    if package.get("packageVerificationCode") != {
        "packageVerificationCodeValue": expected_verification_code
    }:
        fail("SPDX package verification code drift")

    file_ids: set[str] = set()
    raw_spdx_files = sbom.get("files")
    if not isinstance(raw_spdx_files, list):
        fail("SPDX file inventory is missing")
    for entry in raw_spdx_files:
        if not isinstance(entry, dict):
            fail("SPDX file entry is not an object")
        relative = str(entry["fileName"]).removeprefix("./")
        expected_license = file_license(relative)
        if entry.get("licenseConcluded") != expected_license:
            fail(f"SPDX concluded license mismatch for {relative}")
        if entry.get("licenseInfoInFiles") != ["NOASSERTION"]:
            fail(f"SPDX licenseInfoInFiles overclaim for {relative}")
        if entry.get("copyrightText") != "NOASSERTION":
            fail(f"SPDX copyright assertion overclaim for {relative}")
        file_id = entry.get("SPDXID")
        if not isinstance(file_id, str) or file_id in file_ids:
            fail(f"duplicate or invalid SPDX identifier: {file_id}")
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
    if meta.get("schema_version") != 5:
        fail("unsupported release metadata schema")
    if meta.get("source_archive") != archive.name or meta.get("source_archive_sha256") != digest:
        fail("release metadata does not match source archive")
    if meta.get("source_tree_sha256") != sha256(manifest_bytes):
        fail("release metadata source-tree checksum mismatch")
    if meta.get("source_file_count") != len(manifest_records):
        fail("release metadata source-file count mismatch")
    if meta.get("archive_method") != "ZIP_STORED":
        fail("release metadata archive method mismatch")
    if meta.get("version") != project["version"] or meta.get("formal_status") != project["status"]:
        fail("release metadata does not match project metadata")
    source_inventory = meta.get("source_inventory", {})
    if source_inventory != {
        "git_checkout": "tracked_files_only_with_clean_worktree_required",
        "extracted_archive": "filtered_recursive_scan_without_generated_manifest",
        "untracked_git_files_packaged": False,
    }:
        fail("release metadata source-inventory policy drift")
    self_audit = meta.get("source_archive_self_audit", {})
    if not isinstance(self_audit, dict) or self_audit.get("required") is not True:
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
    sbom_profile = meta.get("sbom_profile")
    if sbom_profile != {
        "spdx_version": "SPDX-2.3",
        "required_file_sha1": True,
        "additional_file_sha256": True,
        "package_verification_code": expected_verification_code,
        "release_trust_anchor": "SHA256",
    }:
        fail("release metadata SPDX profile drift")
    release_checksums = meta.get("release_checksums")
    if release_checksums != {
        "path": sums_path.name,
        "algorithm": "SHA256",
        "covered_outputs": sorted(path.name for path in release_files),
    }:
        fail("release metadata complete-checksum inventory drift")
    history = meta.get("history_backup", {})
    if not isinstance(history, dict) or history.get("outputs") != project["history_backup_outputs"]:
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
        entry = meta.get(key)
        if not isinstance(entry, dict):
            fail(f"release metadata omits {key}")
        if entry.get("path") != relative or entry.get("sha256") != current_sha256[relative]:
            fail(f"release metadata mismatch for {key}")

    print(
        f"release verification passed: {len(manifest_records)} source files, "
        f"SPDX 2.3 SHA1/SHA256 inventory, complete release checksums, sha256 {digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
