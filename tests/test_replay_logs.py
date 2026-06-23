from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from verify_replay_logs import EXPECTED_AXIOMS, EXPECTED_DECLARATIONS, parse_reports


class ReplayLogTests(unittest.TestCase):
    def test_parse_multiline_reports(self) -> None:
        text = "\n".join(
            f"'{name}' depends on axioms: [propext,\n Classical.choice, Quot.sound]"
            for name in EXPECTED_DECLARATIONS
        )
        reports = parse_reports(text)
        self.assertEqual(set(reports), set(EXPECTED_DECLARATIONS))
        self.assertTrue(all(axioms == EXPECTED_AXIOMS for axioms in reports.values()))


if __name__ == "__main__":
    unittest.main()
