#!/usr/bin/env python3
"""Create a deterministic source ZIP, complete checksums, SPDX SBOM, and metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

from release_integrity import (
    MAX_ARCHIVE_FILES,
    MAX_ARCHIVE_FILE_BYTES,
    MAX_ARCHIVE_TOTAL_BYTES,
    format_source_manifest,
)
from strict_json import load as load_json
from source_inventory import (
    EXCLUDED_NAMES,
    EXCLUDED_PARTS,
    EXCLUDED_SUFFIXES,
    SourceInventoryError,
    git_worktree_status,
    repository_files as discover_repository_files,
)

ROOT = Path(__file__).resolve().parents[1]
ARCHIVED_EVIDENCE_LOGS = (
    "lean-patch/verification/catalan-build.log",
    "lean-patch/verification/oracle_check_catalan.log",
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha1(data: bytes) -> str:
    """Return SHA-1 for SPDX 2.3 compatibility, never as the release trust anchor."""
    return hashlib.sha1(data).hexdigest()  # noqa: S324 - mandatory SPDX 2.3 file checksum


def repository_files(output_dir: Path) -> list[Path]:
    """Return distributable repository files in canonical path order."""
    return discover_repository_files(ROOT, output_dir)


def zip_info(
    name: str,
    timestamp: tuple[int, int, int, int, int, int],
    executable: bool = False,
) -> zipfile.ZipInfo:
    """Create a normalized ZIP entry.

    ZIP_STORED deliberately avoids zlib-version-dependent compressed bytes. The source
    artifact is small, so cross-runtime byte determinism is more valuable than compression.
    """
    info = zipfile.ZipInfo(name, date_time=timestamp)
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = ((0o755 if executable else 0o644) & 0xFFFF) << 16
    info.flag_bits |= 0x800
    return info


def portable_executable_mode(path: str) -> bool:
    """Return the normalized executable bit used inside the source ZIP."""
    return path.endswith((".py", ".sh"))


def spdx_id(path: str) -> str:
    """Return a readable, collision-resistant SPDX identifier for a source path."""
    slug = "".join(char if char.isalnum() or char in ".-" else "-" for char in path)
    return f"SPDXRef-File-{slug}-{sha256(path.encode('utf-8'))[:12]}"


def spdx_package_verification_code(file_sha1s: Iterable[str]) -> str:
    """Compute the SPDX 2.3 package verification code from file SHA-1 values."""
    ordered = sorted(file_sha1s)
    if any(len(digest) != 40 or any(char not in "0123456789abcdef" for char in digest) for digest in ordered):
        raise ValueError("invalid SHA-1 digest in SPDX package verification input")
    return sha1("".join(ordered).encode("ascii"))


def file_license(path: str) -> str:
    """Return the concluded license under the repository's declared file policy."""
    if path == "main.tex" or path == "Rooted_tree_Catalan_closure.pdf":
        return "CC-BY-4.0"
    if path == "README.md" or path.startswith("docs/"):
        return "CC-BY-4.0"
    if path.endswith((".lean", ".py", ".sh", ".ps1", ".patch", ".yml", ".yaml")):
        return "AGPL-3.0-or-later"
    if path in {"Makefile", "CONTRIBUTING.md", "SECURITY.md", "AGENTS.md"}:
        return "AGPL-3.0-or-later"
    return "NOASSERTION"


def release_checksum_payload(paths: Iterable[Path]) -> bytes:
    """Return a canonical SHA-256 inventory for the complete release output set."""
    records = [(path.name, sha256(path.read_bytes())) for path in paths]
    return format_source_manifest(records)


def reject_symlink_outputs(paths: Iterable[Path]) -> None:
    """Refuse release destinations that could redirect writes outside the output set."""
    for path in paths:
        if path.is_symlink():
            raise SourceInventoryError(f"refusing symbolic-link release output: {path}")


def require_clean_git_source(root: Path, *, allow_dirty: bool) -> None:
    """Reject dirty Git checkouts while permitting extracted source archives."""
    status = git_worktree_status(root)
    if status and not allow_dirty:
        raise SourceInventoryError(
            "refusing to package a dirty Git worktree; commit or stash changes, "
            "or pass --allow-dirty for a non-publication development build"
        )


def _release_date(raw: object) -> datetime:
    if not isinstance(raw, str):
        raise SystemExit("project.json release_date must be an ISO date string")
    try:
        parsed = date.fromisoformat(raw)
    except ValueError as exc:
        raise SystemExit("project.json release_date must be an ISO date") from exc
    if parsed.year < 1980:
        raise SystemExit("project.json release_date predates the ZIP timestamp epoch")
    return datetime(parsed.year, parsed.month, parsed.day, tzinfo=timezone.utc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="release")
    parser.add_argument(
        "--allow-dirty",
        action="store_true",
        help="permit modified tracked files for a development-only package; untracked files remain excluded",
    )
    args = parser.parse_args()

    try:
        require_clean_git_source(ROOT, allow_dirty=args.allow_dirty)
    except SourceInventoryError as exc:
        raise SystemExit(str(exc)) from exc
    project = load_json(ROOT / "project.json")
    if not isinstance(project, dict):
        raise SystemExit("project.json must contain a JSON object")
    version = project["version"]
    release_date = _release_date(project["release_date"])
    timestamp = (release_date.year, release_date.month, release_date.day, 0, 0, 0)
    prefix = f"rooted-tree-catalan-closure-v{version}"
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_path = output_dir / f"{prefix}.zip"
    checksum_path = output_dir / f"{prefix}.zip.sha256"
    sbom_path = output_dir / f"{prefix}.spdx.json"
    metadata_path = output_dir / f"{prefix}.release.json"
    release_sums_path = output_dir / f"{prefix}.SHA256SUMS"
    try:
        reject_symlink_outputs(
            [zip_path, checksum_path, sbom_path, metadata_path, release_sums_path]
        )
    except SourceInventoryError as exc:
        raise SystemExit(str(exc)) from exc

    try:
        files = repository_files(output_dir)
    except SourceInventoryError as exc:
        raise SystemExit(str(exc)) from exc
    selected_paths = {path.relative_to(ROOT).as_posix() for path in files}
    missing_evidence = sorted(set(ARCHIVED_EVIDENCE_LOGS) - selected_paths)
    if missing_evidence:
        raise SystemExit(f"archived verification evidence omitted from source package: {missing_evidence}")

    records: list[dict[str, object]] = []
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        data = path.read_bytes()
        records.append(
            {
                "path": rel,
                "size": len(data),
                "sha1": sha1(data),
                "sha256": sha256(data),
                "license": file_license(rel),
            }
        )
    manifest = format_source_manifest(
        [(str(record["path"]), str(record["sha256"])) for record in records]
    )
    source_tree_sha256 = sha256(manifest)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        for path, record in zip(files, records, strict=True):
            rel = str(record["path"])
            executable = portable_executable_mode(rel)
            archive.writestr(zip_info(f"{prefix}/{rel}", timestamp, executable), path.read_bytes())
        archive.writestr(zip_info(f"{prefix}/SOURCE-MANIFEST.sha256", timestamp), manifest)

    zip_digest = sha256(zip_path.read_bytes())
    checksum_path.write_text(f"{zip_digest}  {zip_path.name}\n", encoding="utf-8", newline="\n")

    namespace_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"{project['repository']}@v{version}")
    package_id = "SPDXRef-Package"
    package_verification_code = spdx_package_verification_code(
        str(record["sha1"]) for record in records
    )
    spdx_files: list[dict[str, object]] = []
    relationships: list[dict[str, str]] = [
        {
            "spdxElementId": "SPDXRef-DOCUMENT",
            "relationshipType": "DESCRIBES",
            "relatedSpdxElement": package_id,
        }
    ]
    for record in records:
        rel = str(record["path"])
        file_id = spdx_id(rel)
        license_id = str(record["license"])
        spdx_files.append(
            {
                "SPDXID": file_id,
                "fileName": f"./{rel}",
                "checksums": [
                    {"algorithm": "SHA1", "checksumValue": record["sha1"]},
                    {"algorithm": "SHA256", "checksumValue": record["sha256"]},
                ],
                "licenseConcluded": license_id,
                # This tool applies repository policy but does not claim to have found a
                # license notice or copyright line inside every individual file.
                "licenseInfoInFiles": ["NOASSERTION"],
                "copyrightText": "NOASSERTION",
            }
        )
        relationships.append(
            {
                "spdxElementId": package_id,
                "relationshipType": "CONTAINS",
                "relatedSpdxElement": file_id,
            }
        )
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{prefix}-source",
        "documentNamespace": f"https://spdx.org/spdxdocs/{prefix}-{namespace_uuid}",
        "documentDescribes": [package_id],
        "creationInfo": {
            "created": release_date.strftime("%Y-%m-%dT00:00:00Z"),
            "creators": ["Tool: rooted-tree-catalan-closure/scripts/package_release.py"],
        },
        "packages": [
            {
                "name": project["name"],
                "SPDXID": package_id,
                "versionInfo": version,
                "packageFileName": zip_path.name,
                "downloadLocation": project["repository"],
                "filesAnalyzed": True,
                "primaryPackagePurpose": "SOURCE",
                "releaseDate": release_date.strftime("%Y-%m-%dT00:00:00Z"),
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "AGPL-3.0-or-later AND CC-BY-4.0",
                "licenseInfoFromFiles": ["NOASSERTION"],
                "copyrightText": "NOASSERTION",
                "packageVerificationCode": {
                    "packageVerificationCodeValue": package_verification_code,
                },
                "checksums": [{"algorithm": "SHA256", "checksumValue": zip_digest}],
            }
        ],
        "files": spdx_files,
        "relationships": relationships,
    }
    sbom_path.write_text(
        json.dumps(sbom, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    finite_evidence = ROOT / "evidence" / "finite-catalan-checks.json"
    theorem_manifest = ROOT / "archive" / "theorem-manifest.json"
    covered_outputs = [zip_path, checksum_path, sbom_path, metadata_path]
    release_meta = {
        "schema_version": 5,
        "name": project["name"],
        "version": version,
        "release_date": project["release_date"],
        "source_archive": zip_path.name,
        "source_archive_sha256": zip_digest,
        "source_tree_sha256": source_tree_sha256,
        "source_file_count": len(records),
        "source_manifest": "SOURCE-MANIFEST.sha256",
        "source_inventory": {
            "git_checkout": "tracked_files_only_with_clean_worktree_required",
            "extracted_archive": "filtered_recursive_scan_without_generated_manifest",
            "untracked_git_files_packaged": False,
        },
        "source_archive_self_audit": {
            "command": "python scripts/check_repository.py",
            "manifest_command": "python scripts/check_source_manifest.py",
            "standalone_zip_command": f"python scripts/verify_source_zip.py {zip_path.name} --checksum {checksum_path.name}",
            "required": True,
            "repackaging_verified": True,
            "host_extracted_modes_authoritative": False,
            "archived_evidence_logs": list(ARCHIVED_EVIDENCE_LOGS),
            "resource_limits": {
                "max_files": MAX_ARCHIVE_FILES,
                "max_file_bytes": MAX_ARCHIVE_FILE_BYTES,
                "max_total_bytes": MAX_ARCHIVE_TOTAL_BYTES,
            },
        },
        "archive_method": "ZIP_STORED",
        "normalized_timestamp": release_date.strftime("%Y-%m-%dT00:00:00Z"),
        "sbom": sbom_path.name,
        "sbom_profile": {
            "spdx_version": "SPDX-2.3",
            "required_file_sha1": True,
            "additional_file_sha256": True,
            "package_verification_code": package_verification_code,
            "release_trust_anchor": "SHA256",
        },
        "release_checksums": {
            "path": release_sums_path.name,
            "algorithm": "SHA256",
            "covered_outputs": sorted(path.name for path in covered_outputs),
        },
        "formal_status": project["status"],
        "unresolved_obligation": project["unresolved_obligation"],
        "recovery_baseline_commit": project["recovery_baseline_commit"],
        "finite_evidence": {
            "path": finite_evidence.relative_to(ROOT).as_posix(),
            "sha256": sha256(finite_evidence.read_bytes()),
        },
        "theorem_manifest": {
            "path": theorem_manifest.relative_to(ROOT).as_posix(),
            "sha256": sha256(theorem_manifest.read_bytes()),
        },
        "upstream": project["upstream"],
        "history_backup": {
            "status": "separate_checksum_and_git_bundle_verify_artifact",
            "outputs": project["history_backup_outputs"],
            "inventory_schema": 2,
            "exact_bundle_heads_verified": True,
            "byte_reproducibility_claim": False,
        },
    }
    metadata_path.write_text(
        json.dumps(release_meta, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    release_sums_path.write_bytes(release_checksum_payload(covered_outputs))

    for path in (*covered_outputs, release_sums_path):
        print(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
