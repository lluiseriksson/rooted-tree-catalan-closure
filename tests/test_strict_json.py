from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from strict_json import StrictJSONError, loads


class StrictJSONTests(unittest.TestCase):
    def test_valid_json_round_trip(self) -> None:
        self.assertEqual(loads('{"a": 1, "nested": {"b": true}}'), {"a": 1, "nested": {"b": True}})

    def test_duplicate_keys_are_rejected_at_any_depth(self) -> None:
        with self.assertRaisesRegex(StrictJSONError, "duplicate JSON key"):
            loads('{"a": 1, "a": 2}', source="duplicate.json")
        with self.assertRaisesRegex(StrictJSONError, "duplicate JSON key"):
            loads('{"outer": {"x": 1, "x": 2}}', source="nested.json")

    def test_nonfinite_numbers_are_rejected(self) -> None:
        for token in ("NaN", "Infinity", "-Infinity"):
            with self.subTest(token=token), self.assertRaises(StrictJSONError):
                loads(f'{{"value": {token}}}', source="nonfinite.json")


if __name__ == "__main__":
    unittest.main()
