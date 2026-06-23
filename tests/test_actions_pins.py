from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_actions_pins import audit_workflows, load_policy


class ActionPinTests(unittest.TestCase):
    def test_repository_workflows_satisfy_policy(self) -> None:
        errors, counts = audit_workflows(ROOT, load_policy())
        self.assertEqual(errors, [])
        self.assertGreaterEqual(counts["actions/checkout"], 1)

    def _audit_line(self, line: str) -> list[str]:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / "archive").mkdir()
            policy = {
                "schema_version": 1,
                "actions": {"actions/checkout": {"major": 7, "required": True}},
            }
            (root / "archive" / "github-actions-policy.json").write_text(
                json.dumps(policy), encoding="utf-8"
            )
            (root / ".github" / "workflows" / "ci.yml").write_text(
                "name: ci\npermissions:\n  contents: read\njobs:\n  x:\n    steps:\n" + line + "\n", encoding="utf-8"
            )
            errors, _ = audit_workflows(root, policy)
            return errors

    def test_mutable_tag_is_rejected(self) -> None:
        errors = self._audit_line("      - uses: actions/checkout@v7 # v7\n        with:\n          persist-credentials: false")
        self.assertTrue(any("full 40-character" in error for error in errors))

    def test_major_comment_mismatch_is_rejected(self) -> None:
        errors = self._audit_line(
            "      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v6\n        with:\n          persist-credentials: false"
        )
        self.assertTrue(any("policy requires v7" in error for error in errors))


    def test_checkout_credentials_must_not_persist(self) -> None:
        errors = self._audit_line(
            "      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7"
        )
        self.assertTrue(any("persist-credentials" in error for error in errors))

    def test_unknown_action_is_rejected(self) -> None:
        errors = self._audit_line(
            "      - uses: unknown/example@0000000000000000000000000000000000000000 # v1"
        )
        self.assertTrue(any("not allowlisted" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
