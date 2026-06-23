from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from strict_json import StrictJSONError, canonical_dumps, loads, loads_canonical


class StrictJSONTests(unittest.TestCase):
    def test_valid_json_round_trip(self) -> None:
        self.assertEqual(loads('{"a": 1, "nested": {"b": true}}'), {"a": 1, "nested": {"b": True}})

    def test_duplicate_keys_are_rejected_at_any_depth(self) -> None:
        with self.assertRaisesRegex(StrictJSONError, "duplicate JSON key"):
            loads('{"a": 1, "a": 2}', source="duplicate.json")
        with self.assertRaisesRegex(StrictJSONError, "duplicate JSON key"):
            loads('{"outer": {"x": 1, "x": 2}}', source="nested.json")

    def test_nonfinite_numbers_are_rejected(self) -> None:
        for token in (
            "NaN",
            "Infinity",
            "-Infinity",
            "1e999",
            "-1e999",
            "1e-999",
            "-1e-999",
        ):
            with self.subTest(token=token), self.assertRaises(StrictJSONError):
                loads(f'{{"value": {token}}}', source="nonfinite.json")


    def test_canonical_json_requires_sorted_stable_bytes(self) -> None:
        value = {"z": 1, "a": {"text": "Prüfer"}}
        canonical = canonical_dumps(value)
        self.assertEqual(
            canonical,
            "{\n"
            "  \"a\": {\n"
            "    \"text\": \"Pr\\u00fcfer\"\n"
            "  },\n"
            "  \"z\": 1\n"
            "}\n",
        )
        self.assertEqual(loads_canonical(canonical, source="canonical.json"), value)
        for noncanonical in (
            '{"a": 1}\n',
            '{\n  "z": 1,\n  "a": 2\n}\n',
            '{\n  "a": 1\n}\n\n',
        ):
            with self.subTest(noncanonical=noncanonical), self.assertRaisesRegex(
                StrictJSONError, "noncanonical JSON"
            ):
                loads_canonical(noncanonical, source="drift.json")

    def test_finite_decimal_numbers_are_preserved(self) -> None:
        self.assertEqual(loads('{"value": 1.25}'), {"value": 1.25})


if __name__ == "__main__":
    unittest.main()
