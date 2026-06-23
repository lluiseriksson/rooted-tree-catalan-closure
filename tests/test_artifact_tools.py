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
from package_release import file_license, zip_info


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
        self.assertEqual(stat.S_IMODE(info.external_attr >> 16), 0o755)
        self.assertEqual(info.date_time, (2026, 6, 23, 0, 0, 0))

    def test_makefile_pins_manuscript_source(self) -> None:
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("TEX := main.tex\n", makefile)
        self.assertIn("TRACKED_PDF := Rooted_tree_Catalan_closure.pdf\n", makefile)
        self.assertNotIn("TEX ?=", makefile)

    def test_file_license_policy(self) -> None:
        self.assertEqual(file_license("main.tex"), "CC-BY-4.0")
        self.assertEqual(file_license("docs/CLAIMS_BOUNDARY.md"), "CC-BY-4.0")
        self.assertEqual(file_license("scripts/check_repository.py"), "AGPL-3.0-or-later")
        self.assertEqual(file_license("lean-patch/X.lean"), "AGPL-3.0-or-later")
        self.assertEqual(file_license("project.json"), "NOASSERTION")


if __name__ == "__main__":
    unittest.main()
