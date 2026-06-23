#!/usr/bin/env python3
"""Audit GitHub Actions references without freezing complete workflow files."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "archive" / "github-actions-policy.json"
WORKFLOW_DIR = ROOT / ".github" / "workflows"
USES_RE = re.compile(
    r"^\s*(?:-\s*)?uses:\s*([^@\s]+)@([^\s#]+)(?:\s+#\s*v([0-9]+))?\s*$"
)
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise ValueError(f"unsupported actions policy schema in {path}")
    actions = data.get("actions")
    if not isinstance(actions, dict) or not actions:
        raise ValueError(f"actions policy has no allowlist in {path}")
    return data


def audit_workflows(
    root: Path = ROOT,
    policy: dict[str, Any] | None = None,
) -> tuple[list[str], Counter[str]]:
    """Return policy violations and per-action reference counts."""
    policy = policy or load_policy(root / "archive" / "github-actions-policy.json")
    allowed = policy["actions"]
    errors: list[str] = []
    counts: Counter[str] = Counter()
    workflow_dir = root / ".github" / "workflows"
    workflows = sorted(workflow_dir.glob("*.yml")) + sorted(workflow_dir.glob("*.yaml"))
    if not workflows:
        errors.append("no GitHub Actions workflows found")
        return errors, counts

    for workflow in workflows:
        workflow_text = workflow.read_text(encoding="utf-8")
        if re.search(r"(?m)^permissions:\s*$", workflow_text) is None:
            errors.append(f"{workflow.relative_to(root).as_posix()}: workflow lacks an explicit permissions block")
        lines = workflow_text.splitlines()
        for line_index, line in enumerate(lines):
            line_number = line_index + 1
            if "uses:" not in line:
                continue
            match = USES_RE.match(line)
            location = f"{workflow.relative_to(root).as_posix()}:{line_number}"
            if match is None:
                errors.append(f"{location}: malformed or unreviewed uses reference: {line.strip()}")
                continue
            action, ref, major_text = match.groups()
            if action.startswith("./"):
                continue
            if action.startswith("docker://"):
                errors.append(f"{location}: docker actions are not allowlisted")
                continue
            spec = allowed.get(action)
            if spec is None:
                errors.append(f"{location}: action is not allowlisted: {action}")
                continue
            counts[action] += 1
            if FULL_SHA_RE.fullmatch(ref) is None:
                errors.append(f"{location}: {action} is not pinned to a full 40-character commit SHA")
            if action == "actions/checkout":
                uses_indent = len(line) - len(line.lstrip())
                step_indent = uses_indent if line.lstrip().startswith("- uses:") else max(0, uses_indent - 2)
                block: list[str] = []
                for following in lines[line_index + 1 :]:
                    stripped = following.lstrip()
                    indent = len(following) - len(stripped)
                    if stripped.startswith("-") and indent <= step_indent:
                        break
                    block.append(following)
                if not any(re.fullmatch(r"\s*persist-credentials:\s*false\s*", item) for item in block):
                    errors.append(f"{location}: checkout must set persist-credentials: false")
            expected_major = spec.get("major")
            if major_text is None:
                errors.append(f"{location}: {action} lacks a reviewed '# vN' release-line comment")
            elif int(major_text) != expected_major:
                errors.append(
                    f"{location}: {action} records v{major_text}, policy requires v{expected_major}"
                )

    for action, spec in sorted(allowed.items()):
        if spec.get("required") and counts[action] == 0:
            errors.append(f"required action is not referenced by any workflow: {action}")
    return errors, counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        policy = load_policy(root / "archive" / "github-actions-policy.json")
        errors, counts = audit_workflows(root, policy)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps({"errors": errors, "references": dict(sorted(counts.items()))}, indent=2))
    else:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if not errors:
            total = sum(counts.values())
            print(f"GitHub Actions pin audit passed: {total} references across {len(counts)} allowlisted actions")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
