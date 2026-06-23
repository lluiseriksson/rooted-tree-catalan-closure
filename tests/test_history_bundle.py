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

    def test_create_and_verify_complete_history_bundle(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rtc-history-test-") as temporary:
            repo = Path(temporary) / "repo"
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
            self.assertEqual(inventory["schema_version"], 2)
            self.assertEqual(inventory["head_commit"], head)
            self.assertEqual(heads["HEAD"], head)
            self.assertEqual(heads["refs/rtc-recovery/HEAD"], head)
            self.assertIn("refs/tags/v0-test", heads)
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
            inventory_path.write_text(json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            sums_path = repo / "history-release" / "rooted-tree-catalan-closure-v1.4.1.history.SHA256SUMS"
            bundle_digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
            inventory_digest = hashlib.sha256(inventory_path.read_bytes()).hexdigest()
            records = sorted([(bundle.name, bundle_digest), (inventory_path.name, inventory_digest)])
            sums_path.write_text("".join(f"{digest}  {name}\n" for name, digest in records), encoding="utf-8")
            failed = subprocess.run(
                [sys.executable, str(VERIFY), "--repository", str(repo)],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(failed.returncode, 0)
            self.assertIn("list-heads", failed.stderr)


if __name__ == "__main__":
    unittest.main()
