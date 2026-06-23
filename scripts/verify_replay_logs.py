#!/usr/bin/env python3
"""Validate full Lean replay logs and emit a machine-readable replay report."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_AXIOMS = ["propext", "Classical.choice", "Quot.sound"]
EXPECTED_DECLARATIONS = [
    "YangMills.KP.rootedChildCount_factorialTreeSum_normalized_le_catalan_of_identity",
    "YangMills.RG.catalanClosure_fixedPoint",
    "YangMills.RG.appendixFHoleHsharpWeightedTreeMarkedRootSum_le_catalan_of_expWeight",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_reports(text: str) -> dict[str, list[str]]:
    pattern = re.compile(r"'([^']+)'\s+depends on axioms:\s*\[([^\]]*)\]", re.S)
    reports: dict[str, list[str]] = {}
    for name, raw_axioms in pattern.findall(text):
        axioms = [part.strip() for part in raw_axioms.replace("\n", " ").split(",") if part.strip()]
        reports[name] = axioms
    return reports


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-log", required=True)
    parser.add_argument("--oracle-log", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--artifact-sha", required=True)
    parser.add_argument("--upstream-sha", required=True)
    parser.add_argument("--lean-toolchain", required=True)
    parser.add_argument("--mathlib-sha", required=True)
    args = parser.parse_args()

    build_log = Path(args.build_log)
    oracle_log = Path(args.oracle_log)
    for path in (build_log, oracle_log):
        if not path.is_file():
            fail(f"missing replay log: {path}")
    build_text = build_log.read_text(encoding="utf-8", errors="replace")
    oracle_text = oracle_log.read_text(encoding="utf-8", errors="replace")
    if "Build completed successfully" not in build_text:
        fail("replay build log lacks a successful build marker")
    if "sorryAx" in oracle_text:
        fail("oracle replay contains sorryAx")
    reports = parse_reports(oracle_text)
    if set(reports) != set(EXPECTED_DECLARATIONS):
        fail(f"unexpected replay declaration set: {sorted(reports)}")
    for name in EXPECTED_DECLARATIONS:
        if reports[name] != EXPECTED_AXIOMS:
            fail(f"unexpected axioms for {name}: {reports[name]}")
    if args.upstream_sha != "1d044a353ac2b69ddca732dd851fb0ab4a94d7af":
        fail(f"unexpected upstream SHA: {args.upstream_sha}")

    report = {
        "schema_version": 1,
        "status": "conditional_adapter_full_replay_passed",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "artifact_sha": args.artifact_sha,
        "upstream_sha": args.upstream_sha,
        "lean_toolchain": args.lean_toolchain,
        "mathlib_sha": args.mathlib_sha,
        "build_log": {"path": build_log.name, "sha256": sha256(build_log)},
        "oracle_log": {"path": oracle_log.name, "sha256": sha256(oracle_log)},
        "declarations": [
            {"name": name, "axioms": reports[name]} for name in EXPECTED_DECLARATIONS
        ],
        "unresolved_obligation": "YangMills.KP.RootedChildFactorialCatalanIdentity n for every n",
    }
    output = Path(args.output)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"full Lean replay logs verified; wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
