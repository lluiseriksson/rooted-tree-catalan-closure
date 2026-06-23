from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_source_manifest import audit_source_manifest
from package_release import spdx_id, zip_info
from release_integrity import (
    MAX_ARCHIVE_FILE_BYTES,
    IntegrityError,
    archive_members,
    format_source_manifest,
    parse_source_manifest,
    safe_extract_members,
    sha256,
    validate_archive_resource_limits,
    validate_portable_relative_path,
    validate_zip_info,
)
from source_inventory import EXCLUDED_NAMES, repository_files
from verify_release import sbom_file_records


class ReleaseIntegrityTests(unittest.TestCase):
    def test_portable_source_paths(self) -> None:
        for path in (
            ".github/workflows/artifact-ci.yml",
            "lean-patch/YangMills/KP/RootedCatalan.lean",
            "README.md",
        ):
            self.assertEqual(validate_portable_relative_path(path), path)
        for path in (
            "",
            "/absolute",
            "../escape",
            "a/../b",
            "a//b",
            "a\\b",
            "AUX.txt",
            "CONIN$.txt",
            "bad:name",
            "trailing. ",
            "cafe\u0301.txt",
        ):
            with self.subTest(path=path), self.assertRaises(IntegrityError):
                validate_portable_relative_path(path)

    def test_manifest_round_trip_is_sorted_and_strict(self) -> None:
        payload = format_source_manifest(
            [
                ("z.txt", sha256(b"z")),
                ("a.txt", sha256(b"a")),
            ]
        )
        self.assertEqual(list(parse_source_manifest(payload.decode("utf-8"))), ["a.txt", "z.txt"])
        with self.assertRaises(IntegrityError):
            parse_source_manifest(payload.decode("utf-8").rstrip("\n"))
        with self.assertRaises(IntegrityError):
            parse_source_manifest(f"{sha256(b'a')}  Readme.md\n{sha256(b'b')}  README.md\n")
        with self.assertRaises(IntegrityError):
            parse_source_manifest("not-a-digest  README.md\n")

    def test_source_inventory_excludes_generated_manifest_and_caches(self) -> None:
        self.assertIn("SOURCE-MANIFEST.sha256", EXCLUDED_NAMES)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "src").mkdir()
            (root / "src" / "keep.py").write_text("print('ok')\n", encoding="utf-8")
            (root / "SOURCE-MANIFEST.sha256").write_text("stale\n", encoding="utf-8")
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "skip.pyc").write_bytes(b"cache")
            (root / "release").mkdir()
            (root / "release" / "skip.zip").write_bytes(b"zip")
            selected = [path.relative_to(root).as_posix() for path in repository_files(root, root / "release")]
            self.assertEqual(selected, ["src/keep.py"])

    def test_extracted_source_manifest_detects_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.txt").write_text("alpha\n", encoding="utf-8")
            manifest = format_source_manifest([("a.txt", sha256((root / "a.txt").read_bytes()))])
            (root / "SOURCE-MANIFEST.sha256").write_bytes(manifest)
            self.assertEqual(audit_source_manifest(root), [])
            (root / "a.txt").write_text("changed\n", encoding="utf-8")
            self.assertTrue(any("checksum drift" in error for error in audit_source_manifest(root)))

    def test_archive_member_validation_and_safe_extraction(self) -> None:
        timestamp = (2026, 6, 23, 0, 0, 0)
        with tempfile.TemporaryDirectory() as temp:
            archive_path = Path(temp) / "source.zip"
            prefix = "artifact-v1.0.0"
            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr(zip_info(f"{prefix}/README.md", timestamp), b"hello\n")
            with zipfile.ZipFile(archive_path) as archive:
                infos = archive.infolist()
                members = archive_members(infos, prefix)
                self.assertEqual(validate_zip_info(infos[0], timestamp), 0o644)
                destination = Path(temp) / "extract"
                extracted = safe_extract_members(archive, members, destination, prefix)
                self.assertEqual((extracted / "README.md").read_bytes(), b"hello\n")

        bad = zipfile.ZipInfo("artifact-v1.0.0/a\\..\\escape.txt")
        with self.assertRaises(IntegrityError):
            archive_members([bad], "artifact-v1.0.0")


    def test_archive_resource_limits_reject_oversized_entries(self) -> None:
        info = zipfile.ZipInfo("artifact-v1.0.0/huge.bin")
        info.file_size = MAX_ARCHIVE_FILE_BYTES + 1
        info.compress_size = info.file_size
        with self.assertRaisesRegex(IntegrityError, "too large"):
            validate_archive_resource_limits([info])

    def test_spdx_inventory_rejects_duplicate_paths(self) -> None:
        digest = sha256(b"x")
        entry = {
            "SPDXID": spdx_id("README.md"),
            "fileName": "./README.md",
            "checksums": [{"algorithm": "SHA256", "checksumValue": digest}],
        }
        with self.assertRaises(IntegrityError):
            sbom_file_records({"files": [entry, dict(entry)]})
        self.assertEqual(sbom_file_records({"files": [entry]}), {"README.md": digest})

    def test_spdx_ids_are_collision_resistant(self) -> None:
        self.assertNotEqual(spdx_id("a/b.txt"), spdx_id("a-b.txt"))
        self.assertTrue(spdx_id("a/b.txt").startswith("SPDXRef-File-a-b.txt-"))


if __name__ == "__main__":
    unittest.main()
