from __future__ import annotations

import json
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from package_release import zip_info
from release_integrity import IntegrityError, format_source_manifest, sha256
from verify_source_zip import verify_source_zip


class StandaloneSourceZipTests(unittest.TestCase):
    timestamp = (2026, 6, 23, 0, 0, 0)
    prefix = "rooted-tree-catalan-closure-v9.8.7"

    def build_archive(
        self,
        directory: Path,
        *,
        script_executable: bool = True,
        duplicate_project_key: bool = False,
    ) -> tuple[Path, Path]:
        if duplicate_project_key:
            project = b'{"name":"rooted-tree-catalan-closure","version":"9.8.7","version":"9.8.7","release_date":"2026-06-23"}\n'
        else:
            project = (
                json.dumps(
                    {
                        "name": "rooted-tree-catalan-closure",
                        "release_date": "2026-06-23",
                        "version": "9.8.7",
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            ).encode()
        script = b"#!/usr/bin/env python3\nprint('ok')\n"
        records = [("project.json", sha256(project)), ("scripts/tool.py", sha256(script))]
        manifest = format_source_manifest(records)
        archive = directory / f"{self.prefix}.zip"
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as output:
            output.writestr(zip_info(f"{self.prefix}/project.json", self.timestamp), project)
            output.writestr(
                zip_info(
                    f"{self.prefix}/scripts/tool.py",
                    self.timestamp,
                    executable=script_executable,
                ),
                script,
            )
            output.writestr(
                zip_info(f"{self.prefix}/SOURCE-MANIFEST.sha256", self.timestamp),
                manifest,
            )
        checksum = directory / f"{archive.name}.sha256"
        checksum.write_text(f"{sha256(archive.read_bytes())}  {archive.name}\n", encoding="utf-8")
        return archive, checksum

    def test_standalone_verifier_uses_archive_modes_not_extracted_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive, checksum = self.build_archive(root)
            extraction = root / "ordinary-extraction"
            with zipfile.ZipFile(archive) as source:
                source.extractall(extraction)
            for path in extraction.rglob("*"):
                if path.is_file():
                    path.chmod(0o644)
            report = verify_source_zip(archive, checksum_path=checksum, expected_version="9.8.7")
            self.assertEqual(report.source_file_count, 2)
            self.assertEqual(report.executable_file_count, 1)
            extracted_mode = stat.S_IMODE((extraction / self.prefix / "scripts/tool.py").stat().st_mode)
            self.assertIn(extracted_mode, {0o644, 0o666})
            self.assertNotEqual(extracted_mode, 0o755)

    def test_script_mode_drift_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive, checksum = self.build_archive(Path(temporary), script_executable=False)
            with self.assertRaisesRegex(IntegrityError, "mode policy mismatch"):
                verify_source_zip(archive, checksum_path=checksum)

    def test_duplicate_project_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            archive, checksum = self.build_archive(Path(temporary), duplicate_project_key=True)
            with self.assertRaisesRegex(IntegrityError, "duplicate JSON key"):
                verify_source_zip(archive, checksum_path=checksum)

    def test_external_checksum_name_and_digest_are_strict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive, checksum = self.build_archive(root)
            checksum.write_text(f"{'0' * 64}  wrong.zip\n", encoding="utf-8")
            with self.assertRaises(IntegrityError):
                verify_source_zip(archive, checksum_path=checksum)


if __name__ == "__main__":
    unittest.main()
