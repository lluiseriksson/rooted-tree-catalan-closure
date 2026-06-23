from __future__ import annotations

import hashlib
import stat
import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_repository import git_blob_sha, parse_oracle_axioms, strip_lean_comments_and_strings
from package_release import (
    ARCHIVED_EVIDENCE_LOGS,
    file_license,
    portable_executable_mode,
    reject_symlink_outputs,
    release_checksum_payload,
    repository_files,
    spdx_package_verification_code,
    zip_info,
)


class ArtifactToolTests(unittest.TestCase):
    def test_git_blob_sha(self) -> None:
        data = b"hello\n"
        self.assertEqual(git_blob_sha(data), hashlib.sha1(b"blob 6\0" + data).hexdigest())

    def test_nested_lean_comments_and_strings(self) -> None:
        source = (
            "theorem x : True := by\n"
            "  /- sorry /- axiom -/ admit -/\n"
            '  let s := "sorryAx"\n'
            "  exact True.intro\n"
        )
        stripped = strip_lean_comments_and_strings(source)
        self.assertNotIn("sorry", stripped)
        self.assertNotIn("axiom", stripped)
        self.assertNotIn("admit", stripped)
        self.assertIn("exact True.intro", stripped)

    def test_oracle_axiom_parser(self) -> None:
        text = "x depends on axioms: [propext, Classical.choice,\n Quot.sound]"
        self.assertEqual(
            parse_oracle_axioms(text),
            [{"propext", "Classical.choice", "Quot.sound"}],
        )

    def test_zip_entries_are_stored_and_normalized(self) -> None:
        info = zip_info("artifact/example.py", (2026, 6, 23, 0, 0, 0), executable=True)
        self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
        self.assertEqual(info.create_system, 3)
        raw_mode = info.external_attr >> 16
        self.assertTrue(stat.S_ISREG(raw_mode))
        self.assertEqual(stat.S_IMODE(raw_mode), 0o755)
        self.assertEqual(info.flag_bits, 0)
        self.assertEqual(info.date_time, (2026, 6, 23, 0, 0, 0))

    def test_portable_executable_mode_ignores_host_permissions(self) -> None:
        self.assertTrue(portable_executable_mode("scripts/check_repository.py"))
        self.assertTrue(portable_executable_mode("scripts/bootstrap_upstream_patch.sh"))
        self.assertFalse(portable_executable_mode("README.md"))
        self.assertFalse(portable_executable_mode(".github/workflows/artifact-ci.yml"))

    def test_spdx_package_verification_code_uses_sorted_sha1_values(self) -> None:
        values = [hashlib.sha1(b"b").hexdigest(), hashlib.sha1(b"a").hexdigest()]
        expected = hashlib.sha1("".join(sorted(values)).encode("ascii")).hexdigest()
        self.assertEqual(spdx_package_verification_code(values), expected)

    def test_complete_release_checksum_payload_is_canonical(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            left = root / "b.json"
            right = root / "a.zip"
            left.write_bytes(b"b")
            right.write_bytes(b"a")
            payload = release_checksum_payload([left, right]).decode("utf-8")
            self.assertEqual(payload.splitlines()[0].split("  ", 1)[1], "a.zip")
            self.assertEqual(payload.splitlines()[1].split("  ", 1)[1], "b.json")

    def test_release_outputs_must_not_be_symbolic_links(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "target"
            target.write_bytes(b"target")
            link = root / "artifact.zip"
            try:
                link.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symbolic links unavailable: {exc}")
            with self.assertRaisesRegex(Exception, "symbolic-link release output"):
                reject_symlink_outputs([link])

    def test_makefile_pins_manuscript_source(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("TEX := main.tex\n", makefile)
        self.assertIn("TRACKED_PDF := Rooted_tree_Catalan_closure.pdf\n", makefile)
        self.assertNotIn("TEX ?=", makefile)


    def test_powershell_paper_build_is_non_destructive_by_default(self) -> None:
        script = (ROOT / "build.ps1").read_text(encoding="utf-8")
        self.assertIn("[switch]$RefreshTrackedPdf", script)
        self.assertIn("[switch]$RequirePdfTools", script)
        self.assertIn("--require-tools", script)
        self.assertIn("--rebuilt", script)
        self.assertIn("if ($RefreshTrackedPdf)", script)
        self.assertIn("$builtPdf", script)
        self.assertIn("scripts/check_pdf.py", script)
        self.assertIn("without modifying the tracked artifact", script)

    def test_source_package_keeps_archived_lean_logs(self) -> None:
        selected = {path.relative_to(ROOT).as_posix() for path in repository_files(ROOT / "release")}
        self.assertTrue(set(ARCHIVED_EVIDENCE_LOGS) <= selected)

    def test_file_license_policy(self) -> None:
        self.assertEqual(file_license("main.tex"), "CC-BY-4.0")
        self.assertEqual(file_license("docs/CLAIMS_BOUNDARY.md"), "CC-BY-4.0")
        self.assertEqual(file_license("scripts/check_repository.py"), "AGPL-3.0-or-later")
        self.assertEqual(file_license("lean-patch/X.lean"), "AGPL-3.0-or-later")
        self.assertEqual(file_license("project.json"), "NOASSERTION")


if __name__ == "__main__":
    unittest.main()
