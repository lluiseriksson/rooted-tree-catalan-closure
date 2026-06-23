from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CREATE = ROOT / "scripts" / "create_history_bundle.py"
VERIFY = ROOT / "scripts" / "verify_history_bundle.py"


class HistoryBundleTests(unittest.TestCase):
    def run_git(self, repo: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            text=True,
            capture_output=True,
            check=True,
        )
        return result.stdout.strip()

    def fixture_repository(self, root: Path, *, annotated_release_tag: bool = True) -> tuple[Path, str, str]:
        repo = root / "repo"
        repo.mkdir()
        self.run_git(repo, "init", "-b", "master")
        self.run_git(repo, "config", "user.name", "Test User")
        self.run_git(repo, "config", "user.email", "test@example.invalid")
        (repo / "project.json").write_text(
            json.dumps(
                {
                    "name": "rooted-tree-catalan-closure",
                    "version": "1.4.1",
                    "repository": "https://example.invalid/rooted-tree-catalan-closure",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (repo / "first.txt").write_text("first\n", encoding="utf-8")
        self.run_git(repo, "add", ".")
        self.run_git(repo, "commit", "-m", "first")
        first = self.run_git(repo, "rev-parse", "HEAD")
        self.run_git(repo, "tag", "v0-test")
        (repo / "second.txt").write_text("second\n", encoding="utf-8")
        self.run_git(repo, "add", "second.txt")
        self.run_git(repo, "commit", "-m", "second")
        head = self.run_git(repo, "rev-parse", "HEAD")
        if annotated_release_tag:
            self.run_git(repo, "tag", "-a", "v1.4.1", "-m", "release 1.4.1")
        else:
            self.run_git(repo, "tag", "v1.4.1")
        return repo, first, head

    def test_create_and_verify_complete_history_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rtc-history-test-") as temporary:
            repo, first, head = self.fixture_repository(Path(temporary))

            subprocess.run(
                [sys.executable, str(CREATE), "--repository", str(repo)],
                check=True,
            )
            subprocess.run(
                [sys.executable, str(VERIFY), "--repository", str(repo)],
                check=True,
            )
            inventory_path = (
                repo
                / "history-release"
                / "rooted-tree-catalan-closure-v1.4.1.history.json"
            )
            inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
            heads = {entry["ref"]: entry["oid"] for entry in inventory["bundle_heads"]}
            self.assertEqual(inventory["schema_version"], 3)
            self.assertEqual(inventory["object_format"], "sha1")
            self.assertEqual(inventory["head_commit"], head)
            self.assertEqual(heads["HEAD"], head)
            self.assertEqual(heads["refs/rtc-recovery/HEAD"], head)
            self.assertIn("refs/tags/v0-test", heads)
            self.assertIn("refs/tags/v1.4.1", heads)
            self.assertEqual(inventory["release_tag"], "refs/tags/v1.4.1")
            self.assertEqual(inventory["release_tag_commit"], head)
            self.assertTrue(inventory["release_tag_annotated"])
            self.assertEqual(
                inventory["restoration_verification"],
                {
                    "exact_refs": True,
                    "git_fsck_full_strict": True,
                    "mirror_clone": True,
                    "restored_ref_count": len(heads) - 1,
                },
            )
            bundle = repo / "history-release" / inventory["bundle"]
            clone = Path(temporary) / "clone"
            subprocess.run(["git", "clone", str(bundle), str(clone)], check=True, capture_output=True)
            subprocess.run(["git", "cat-file", "-e", f"{first}^{{commit}}"], cwd=clone, check=True)
            subprocess.run(["git", "cat-file", "-e", f"{head}^{{commit}}"], cwd=clone, check=True)

            # Recompute the sidecar after deleting one recorded head. The verifier must
            # still reject the inventory because it no longer matches list-heads.
            inventory["bundle_heads"] = [
                entry for entry in inventory["bundle_heads"] if entry["ref"] != "refs/tags/v0-test"
            ]
            inventory["restoration_verification"]["restored_ref_count"] -= 1
            inventory_path.write_text(
                json.dumps(inventory, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            sums_path = repo / "history-release" / "rooted-tree-catalan-closure-v1.4.1.history.SHA256SUMS"
            bundle_digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
            inventory_digest = hashlib.sha256(inventory_path.read_bytes()).hexdigest()
            records = sorted([(bundle.name, bundle_digest), (inventory_path.name, inventory_digest)])
            sums_path.write_text(
                "".join(f"{digest}  {name}\n" for name, digest in records),
                encoding="utf-8",
            )
            failed = subprocess.run(
                [sys.executable, str(VERIFY), "--repository", str(repo)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("list-heads", failed.stderr)

    def test_lightweight_release_tag_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rtc-history-lightweight-") as temporary:
            repo, _, _ = self.fixture_repository(
                Path(temporary), annotated_release_tag=False
            )
            failed = subprocess.run(
                [sys.executable, str(CREATE), "--repository", str(repo)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("not an annotated tag", failed.stderr)

    def test_history_directory_rejects_extra_outputs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rtc-history-extra-") as temporary:
            repo, _, _ = self.fixture_repository(Path(temporary))
            subprocess.run(
                [sys.executable, str(CREATE), "--repository", str(repo)],
                check=True,
            )
            (repo / "history-release" / "unexpected.txt").write_text(
                "unexpected\n", encoding="utf-8"
            )
            failed = subprocess.run(
                [sys.executable, str(VERIFY), "--repository", str(repo)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("output inventory mismatch", failed.stderr)


if __name__ == "__main__":
    unittest.main()
