#!/usr/bin/env python3
"""Generate or verify finite exact checks of the rooted-tree Catalan identity.

This is independent computational evidence, not a Lean proof.  Three exact integer
computations are compared:

1. exhaustive Prüfer-word enumeration;
2. exhaustive spanning-tree enumeration by edge subsets (for smaller orders); and
3. summation over Prüfer occurrence profiles.

For trees on ``n + 1`` labelled vertices rooted at ``0``, Prüfer multiplicities
``a_v`` give rooted child counts ``a_0 + 1`` at the root and ``a_v`` elsewhere.
Consequently the tree weight is ``(a_0 + 1)! * product_{v>0} a_v!``.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from dataclasses import asdict, dataclass
from math import comb, factorial
from pathlib import Path
from typing import Iterator, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVIDENCE = ROOT / "evidence" / "finite-catalan-checks.json"
SCHEMA_VERSION = 1
METHODS = (
    "exhaustive_prufer_words",
    "exhaustive_edge_subset_trees",
    "prufer_occurrence_profiles",
)


def catalan(n: int) -> int:
    """Return the nth Catalan number exactly."""
    if n < 0:
        raise ValueError("n must be nonnegative")
    return comb(2 * n, n) // (n + 1)


def expected_weighted_sum(n: int) -> int:
    """Return ``n! * Catalan(n)``, the unnormalised target identity."""
    return factorial(n) * catalan(n)


def rooted_weight_from_prufer_counts(counts: Sequence[int]) -> int:
    """Compute the rooted child-factorial weight from Prüfer multiplicities."""
    if not counts:
        raise ValueError("counts must contain the root")
    weight = factorial(counts[0] + 1)
    for count in counts[1:]:
        if count < 0:
            raise ValueError("multiplicities must be nonnegative")
        weight *= factorial(count)
    return weight


def rooted_weight_from_degrees(degrees: Sequence[int]) -> int:
    """Compute the rooted child-factorial weight from degrees of a rooted tree."""
    if not degrees:
        raise ValueError("degrees must contain the root")
    if len(degrees) == 1:
        if degrees[0] != 0:
            raise ValueError("the one-vertex tree must have degree zero")
        return 1
    if degrees[0] <= 0 or any(degree <= 0 for degree in degrees[1:]):
        raise ValueError("a nontrivial tree has no isolated vertex")
    weight = factorial(degrees[0])
    for degree in degrees[1:]:
        weight *= factorial(degree - 1)
    return weight


def prufer_weight_sum(n: int) -> tuple[int, int]:
    """Exhaustively sum weights over all Prüfer words for order ``n``."""
    if n < 0:
        raise ValueError("n must be nonnegative")
    if n == 0:
        return 1, 1
    vertices = n + 1
    word_length = n - 1
    total = 0
    words = 0
    for word in itertools.product(range(vertices), repeat=word_length):
        counts = [0] * vertices
        for vertex in word:
            counts[vertex] += 1
        total += rooted_weight_from_prufer_counts(counts)
        words += 1
    return total, words


def weak_compositions(total: int, parts: int) -> Iterator[tuple[int, ...]]:
    """Yield weak compositions of ``total`` into ``parts`` ordered parts."""
    if total < 0 or parts <= 0:
        raise ValueError("total must be nonnegative and parts positive")
    if parts == 1:
        yield (total,)
        return
    for head in range(total + 1):
        for tail in weak_compositions(total - head, parts - 1):
            yield (head, *tail)


def profile_weight_sum(n: int) -> tuple[int, int]:
    """Sum exact word multiplicities grouped by Prüfer occurrence profile."""
    if n < 0:
        raise ValueError("n must be nonnegative")
    if n == 0:
        return 1, 1
    vertices = n + 1
    word_length = n - 1
    word_factorial = factorial(word_length)
    total = 0
    profiles = 0
    for counts in weak_compositions(word_length, vertices):
        multiplicity = word_factorial
        for count in counts:
            multiplicity //= factorial(count)
        total += multiplicity * rooted_weight_from_prufer_counts(counts)
        profiles += 1
    return total, profiles


class DisjointSet:
    """Minimal disjoint-set structure used by edge-subset tree enumeration."""

    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, value: int) -> int:
        root = value
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[value] != value:
            parent = self.parent[value]
            self.parent[value] = root
            value = parent
        return root

    def union(self, left: int, right: int) -> bool:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return False
        if self.rank[left_root] < self.rank[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        if self.rank[left_root] == self.rank[right_root]:
            self.rank[left_root] += 1
        return True


def graph_weight_sum(n: int) -> tuple[int, int]:
    """Enumerate all spanning trees as acyclic edge subsets of the complete graph."""
    if n < 0:
        raise ValueError("n must be nonnegative")
    vertices = n + 1
    if vertices == 1:
        return 1, 1
    all_edges = tuple(itertools.combinations(range(vertices), 2))
    total = 0
    tree_count = 0
    for edges in itertools.combinations(all_edges, vertices - 1):
        dsu = DisjointSet(vertices)
        degrees = [0] * vertices
        acyclic = True
        for left, right in edges:
            if not dsu.union(left, right):
                acyclic = False
                break
            degrees[left] += 1
            degrees[right] += 1
        if not acyclic:
            continue
        tree_count += 1
        total += rooted_weight_from_degrees(degrees)
    return total, tree_count


@dataclass(frozen=True)
class OrderEvidence:
    n: int
    vertices: int
    catalan: int
    factorial: int
    expected_weighted_sum: int
    prufer_word_count: int
    prufer_weighted_sum: int
    profile_count: int
    profile_weighted_sum: int
    graph_tree_count: int | None
    graph_weighted_sum: int | None


def compute_order(n: int, graph_max_n: int) -> OrderEvidence:
    expected = expected_weighted_sum(n)
    prufer_sum, word_count = prufer_weight_sum(n)
    profile_sum, profile_count = profile_weight_sum(n)
    if prufer_sum != expected:
        raise AssertionError(f"Prüfer sum failed at n={n}: {prufer_sum} != {expected}")
    if profile_sum != expected:
        raise AssertionError(f"profile sum failed at n={n}: {profile_sum} != {expected}")
    expected_words = 1 if n == 0 else (n + 1) ** max(n - 1, 0)
    if word_count != expected_words:
        raise AssertionError(f"Prüfer word count failed at n={n}: {word_count} != {expected_words}")
    if n == 0:
        expected_profiles = 1
    else:
        expected_profiles = comb(2 * n - 1, n)
    if profile_count != expected_profiles:
        raise AssertionError(
            f"profile count failed at n={n}: {profile_count} != {expected_profiles}"
        )
    graph_count: int | None = None
    graph_sum: int | None = None
    if n <= graph_max_n:
        graph_sum, graph_count = graph_weight_sum(n)
        expected_trees = 1 if n == 0 else (n + 1) ** max(n - 1, 0)
        if graph_count != expected_trees:
            raise AssertionError(
                f"graph tree count failed at n={n}: {graph_count} != {expected_trees}"
            )
        if graph_sum != expected:
            raise AssertionError(f"graph sum failed at n={n}: {graph_sum} != {expected}")
    return OrderEvidence(
        n=n,
        vertices=n + 1,
        catalan=catalan(n),
        factorial=factorial(n),
        expected_weighted_sum=expected,
        prufer_word_count=word_count,
        prufer_weighted_sum=prufer_sum,
        profile_count=profile_count,
        profile_weighted_sum=profile_sum,
        graph_tree_count=graph_count,
        graph_weighted_sum=graph_sum,
    )


def build_evidence(max_n: int, graph_max_n: int) -> dict[str, object]:
    if max_n < 0:
        raise ValueError("max_n must be nonnegative")
    if graph_max_n < 0 or graph_max_n > max_n:
        raise ValueError("graph_max_n must satisfy 0 <= graph_max_n <= max_n")
    results = [asdict(compute_order(n, graph_max_n)) for n in range(max_n + 1)]
    statement = (
        "For complete-graph spanning trees on n+1 labelled vertices rooted at 0, "
        "sum_T product_v childCount_T(v)! = n! * Catalan(n)."
    )
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "statement": statement,
        "status": "finite_exact_computational_evidence_not_formal_proof",
        "root": 0,
        "max_n": max_n,
        "graph_max_n": graph_max_n,
        "methods": list(METHODS),
        "normalization": "divide expected_weighted_sum by n! to obtain Catalan(n)",
        "results": results,
    }
    canonical_results = json.dumps(results, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["results_sha256"] = hashlib.sha256(canonical_results).hexdigest()
    return payload


def canonical_json(payload: dict[str, object]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def evidence_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-n", type=int, default=8)
    parser.add_argument("--graph-max-n", type=int, default=7)
    parser.add_argument("--evidence", default=str(DEFAULT_EVIDENCE.relative_to(ROOT)))
    parser.add_argument("--write", action="store_true", help="write the deterministic evidence JSON")
    parser.add_argument(
        "--no-evidence-check",
        action="store_true",
        help="compute and print results without comparing the tracked evidence file",
    )
    args = parser.parse_args()
    try:
        payload = build_evidence(args.max_n, args.graph_max_n)
    except (AssertionError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    rendered = canonical_json(payload)
    path = evidence_path(args.evidence)
    if args.write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8", newline="\n")
        print(f"wrote {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    elif not args.no_evidence_check:
        if not path.is_file():
            print(f"ERROR: missing evidence file: {path}", file=sys.stderr)
            return 1
        tracked = path.read_text(encoding="utf-8")
        if tracked != rendered:
            print(
                "ERROR: finite Catalan evidence is stale; run "
                "python scripts/check_finite_catalan.py --write",
                file=sys.stderr,
            )
            return 1
    last = payload["results"][-1]
    assert isinstance(last, dict)
    print(
        "finite Catalan checks passed for "
        f"0 <= n <= {args.max_n}; exhaustive edge-subset trees through n={args.graph_max_n}; "
        f"last weighted sum {last['expected_weighted_sum']}"
    )
    print("status: exact finite computation only; the general Lean identity remains open")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
