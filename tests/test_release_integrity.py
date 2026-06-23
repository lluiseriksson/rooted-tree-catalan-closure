from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_source_manifest import audit_source_manifest
from package_release import require_clean_git_source, spdx_id, zip_info
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
    validate_source_payload_limits,
    validate_zip_info,
)
from source_inventory import (
    EXCLUDED_NAMES,
    git_worktree_status,
    repository_files,
    source_exclusion_reason,
)
from verify_release import (
    sbom_file_records,
    validate_release_output_directory,
    verify_release_checksum_inventory,
)


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
            "line\u2028separator.txt",
            "bidi\u202espell.txt",
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

    @unittest.skipUnless(shutil.which("git"), "git executable required")
    def test_git_inventory_is_tracked_only_and_reports_dirty_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            (root / "tracked.txt").write_text("tracked\n", encoding="utf-8")
            subprocess.run(["git", "add", "tracked.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
            self.assertEqual(git_worktree_status(root), b"")

            (root / "untracked-secret.txt").write_text("secret\n", encoding="utf-8")
            selected = [path.relative_to(root).as_posix() for path in repository_files(root)]
            self.assertEqual(selected, ["tracked.txt"])
            self.assertTrue(git_worktree_status(root))
            with self.assertRaisesRegex(Exception, "dirty Git worktree"):
                require_clean_git_source(root, allow_dirty=False)
            require_clean_git_source(root, allow_dirty=True)

    @unittest.skipUnless(shutil.which("git"), "git executable required")
    def test_tracked_symbolic_links_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            (root / "target.txt").write_text("target\n", encoding="utf-8")
            try:
                (root / "link.txt").symlink_to("target.txt")
            except OSError as exc:
                self.skipTest(f"symbolic links unavailable: {exc}")
            subprocess.run(["git", "add", "target.txt", "link.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
            with self.assertRaisesRegex(Exception, "tracked symbolic links"):
                repository_files(root)

    def test_distribution_policy_rejects_repository_internal_paths(self) -> None:
        self.assertIsNotNone(source_exclusion_reason(".git/config"))
        self.assertIsNotNone(source_exclusion_reason("release/old.zip"))
        self.assertIsNotNone(source_exclusion_reason("nested/__pycache__/cache.pyc"))
        self.assertIsNone(source_exclusion_reason("scripts/check_repository.py"))

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



    def test_zip_metadata_requires_regular_file_type_and_canonical_utf8_flag(self) -> None:
        timestamp = (2026, 6, 23, 0, 0, 0)
        canonical = zip_info("artifact-v1.0.0/README.md", timestamp)
        self.assertEqual(validate_zip_info(canonical, timestamp), 0o644)

        missing_type = zipfile.ZipInfo("artifact-v1.0.0/README.md", date_time=timestamp)
        missing_type.compress_type = zipfile.ZIP_STORED
        missing_type.create_system = 3
        missing_type.external_attr = 0o644 << 16
        with self.assertRaisesRegex(IntegrityError, "regular Unix file"):
            validate_zip_info(missing_type, timestamp)

        wrong_flag = zip_info("artifact-v1.0.0/README.md", timestamp)
        wrong_flag.flag_bits = 0x800
        with self.assertRaisesRegex(IntegrityError, "UTF-8 flag policy"):
            validate_zip_info(wrong_flag, timestamp)


    def test_producer_resource_limits_fail_before_writing(self) -> None:
        self.assertEqual(validate_source_payload_limits([("a.txt", 10)], 75), (2, 85))
        with self.assertRaisesRegex(IntegrityError, "too large"):
            validate_source_payload_limits(
                [("huge.bin", MAX_ARCHIVE_FILE_BYTES + 1)],
                75,
            )

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
            "checksums": [
                {"algorithm": "SHA1", "checksumValue": "1" * 40},
                {"algorithm": "SHA256", "checksumValue": digest},
            ],
        }
        with self.assertRaises(IntegrityError):
            sbom_file_records({"files": [entry, dict(entry)]})
        self.assertEqual(
            sbom_file_records({"files": [entry]}),
            {"README.md": {"SHA1": "1" * 40, "SHA256": digest}},
        )

    def test_complete_release_checksum_inventory_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "artifact.zip"
            metadata = root / "artifact.json"
            archive.write_bytes(b"zip")
            metadata.write_bytes(b"metadata")
            sums = root / "artifact.SHA256SUMS"
            sums.write_bytes(
                format_source_manifest(
                    [
                        (archive.name, sha256(archive.read_bytes())),
                        (metadata.name, sha256(metadata.read_bytes())),
                    ]
                )
            )
            verify_release_checksum_inventory(sums, [archive, metadata])
            metadata.write_bytes(b"changed")
            with self.assertRaisesRegex(IntegrityError, "checksum mismatch"):
                verify_release_checksum_inventory(sums, [archive, metadata])

    def test_release_output_directory_requires_exact_regular_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            expected = {"artifact.zip", "artifact.SHA256SUMS"}
            for name in expected:
                (root / name).write_bytes(name.encode("ascii"))
            validate_release_output_directory(root, expected)

            extra = root / "unexpected"
            extra.mkdir()
            with self.assertRaisesRegex(IntegrityError, "non-regular output entries"):
                validate_release_output_directory(root, expected)
            extra.rmdir()

            target = root / "target"
            target.write_bytes(b"target")
            link = root / "redirected"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symbolic links unavailable: {exc}")
            with self.assertRaisesRegex(IntegrityError, "non-regular output entries"):
                validate_release_output_directory(root, expected | {"target", "redirected"})

    def test_spdx_ids_are_collision_resistant(self) -> None:
        self.assertNotEqual(spdx_id("a/b.txt"), spdx_id("a-b.txt"))
        self.assertTrue(spdx_id("a/b.txt").startswith("SPDXRef-File-a-b.txt-"))


if __name__ == "__main__":
    unittest.main()
