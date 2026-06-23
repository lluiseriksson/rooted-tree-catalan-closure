from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_metadata_consistency import check_metadata_consistency

METADATA_FILES = (
    "project.json",
    "CITATION.cff",
    "CITATION.bib",
    "codemeta.json",
    ".zenodo.json",
    "archive/theorem-manifest.json",
    "CHANGELOG.md",
    "RELEASE_NOTES.md",
)


class MetadataConsistencyTests(unittest.TestCase):
    def copy_metadata(self, destination: Path) -> None:
        for relative in METADATA_FILES:
            source = ROOT / relative
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    def test_repository_metadata_is_consistent(self) -> None:
        self.assertEqual(check_metadata_consistency(ROOT), [])

    def test_version_drift_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.copy_metadata(root)
            codemeta_path = root / "codemeta.json"
            codemeta = json.loads(codemeta_path.read_text(encoding="utf-8"))
            codemeta["version"] = "0.0.0"
            codemeta_path.write_text(json.dumps(codemeta, indent=2) + "\n", encoding="utf-8")
            self.assertIn("CodeMeta version drift", check_metadata_consistency(root))

    def test_formal_boundary_drift_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.copy_metadata(root)
            manifest_path = root / "archive" / "theorem-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["formal_boundary"]["closed_exact_catalan_identity"] = True
            manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            errors = check_metadata_consistency(root)
            self.assertTrue(any("closed_exact_catalan_identity" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
