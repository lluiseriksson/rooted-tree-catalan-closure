from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_finite_catalan import (
    build_evidence,
    catalan,
    expected_weighted_sum,
    graph_weight_sum,
    profile_weight_sum,
    prufer_weight_sum,
    rooted_weight_from_degrees,
    rooted_weight_from_prufer_counts,
    weak_compositions,
)


class FiniteCatalanTests(unittest.TestCase):
    def test_catalan_values(self) -> None:
        self.assertEqual([catalan(n) for n in range(9)], [1, 1, 2, 5, 14, 42, 132, 429, 1430])

    def test_weight_relations(self) -> None:
        # Prüfer word [0, 2] on four vertices has multiplicities (1, 0, 1, 0)
        # and degrees (2, 1, 2, 1).
        self.assertEqual(rooted_weight_from_prufer_counts((1, 0, 1, 0)), 2)
        self.assertEqual(rooted_weight_from_degrees((2, 1, 2, 1)), 2)

    def test_weak_compositions(self) -> None:
        values = list(weak_compositions(2, 3))
        self.assertEqual(len(values), 6)
        self.assertEqual(values[0], (0, 0, 2))
        self.assertEqual(values[-1], (2, 0, 0))
        self.assertTrue(all(sum(value) == 2 for value in values))

    def test_three_exact_methods_agree(self) -> None:
        for n in range(6):
            expected = expected_weighted_sum(n)
            self.assertEqual(prufer_weight_sum(n)[0], expected)
            self.assertEqual(profile_weight_sum(n)[0], expected)
            self.assertEqual(graph_weight_sum(n)[0], expected)

    def test_tracked_evidence_matches_generator(self) -> None:
        tracked = json.loads((ROOT / "evidence" / "finite-catalan-checks.json").read_text(encoding="utf-8"))
        self.assertEqual(tracked, build_evidence(max_n=8, graph_max_n=7))
        self.assertEqual(tracked["status"], "finite_exact_computational_evidence_not_formal_proof")


if __name__ == "__main__":
    unittest.main()
