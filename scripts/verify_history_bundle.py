#!/usr/bin/env python3
"""Verify a Git history bundle, exact head inventory, and SHA-256 sidecars."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from create_history_bundle import OID_RE, TEMP_REF, parse_bundle_heads
from release_integrity import IntegrityError, portable_path_key, sha256_file, validate_portable_relative_path
from strict_json import StrictJSONError, load as load_json

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def parse_sums(text: str) -> dict[str, str]:
    """Parse a canonical basename-only SHA-256 sidecar."""
    if not text or not text.endswith("\n"):
        raise IntegrityError("history checksum file is empty or lacks its final newline")
    records: dict[str, str] = {}
    folded: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        try:
            digest, name = line.split("  ", 1)
        except ValueError as exc:
            raise IntegrityError(f"malformed checksum line {line_number}: {line!r}") from exc
        validate_portable_relative_path(name)
        if "/" in name:
            raise IntegrityError(f"history checksum entry is not a basename: {name!r}")
        if SHA256_RE.fullmatch(digest) is None:
            raise IntegrityError(f"invalid SHA-256 digest for {name}")
        if name in records:
            raise IntegrityError(f"duplicate checksum entry: {name}")
        key = portable_path_key(name)
        if key in folded:
            raise IntegrityError(f"case-insensitive checksum collision: {folded[key]!r} and {name!r}")
        records[name] = digest
        folded[key] = name
    if list(records) != sorted(records):
        raise IntegrityError("history checksum records are not in canonical order")
    return records


def validate_inventory_heads(payload: dict[str, Any]) -> list[dict[str, str]]:
    raw_heads = payload.get("bundle_heads")
    if not isinstance(raw_heads, list) or not raw_heads:
        raise IntegrityError("history inventory contains no bundle_heads")
    heads: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, entry in enumerate(raw_heads, 1):
        if not isinstance(entry, dict) or set(entry) != {"oid", "ref"}:
            raise IntegrityError(f"bundle head {index} must contain exactly oid and ref")
        oid = entry.get("oid")
        ref = entry.get("ref")
        if not isinstance(oid, str) or OID_RE.fullmatch(oid) is None:
            raise IntegrityError(f"bundle head {index} has an invalid object id")
        if not isinstance(ref, str) or not ref or ref in seen:
            raise IntegrityError(f"bundle head {index} has a duplicate or empty ref")
        if ref != "HEAD" and not ref.startswith("refs/"):
            raise IntegrityError(f"bundle head {index} has a noncanonical ref: {ref!r}")
        seen.add(ref)
        heads.append({"oid": oid, "ref": ref})
    if heads != sorted(heads, key=lambda item: item["ref"]):
        raise IntegrityError("bundle_heads are not in canonical ref order")
    return heads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--release-dir", default="history-release")
    args = parser.parse_args()

    root = args.repository.resolve()
    project_path = root / "project.json"
    try:
        project = load_json(project_path)
    except StrictJSONError as exc:
        return fail(str(exc))
    if not isinstance(project, dict):
        return fail(f"{project_path} must contain a JSON object")
    prefix = f"rooted-tree-catalan-closure-v{project['version']}"
    directory = Path(args.release_dir)
    if not directory.is_absolute():
        directory = root / directory
    bundle = directory / f"{prefix}-history.bundle"
    inventory = directory / f"{prefix}.history.json"
    sums = directory / f"{prefix}.history.SHA256SUMS"
    for path in (bundle, inventory, sums):
        if not path.is_file():
            return fail(f"missing history artifact: {path}")

    try:
        expected = parse_sums(sums.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, IntegrityError) as exc:
        return fail(str(exc))
    if set(expected) != {bundle.name, inventory.name}:
        return fail("history checksum inventory has unexpected files")
    for path in (bundle, inventory):
        if sha256_file(path) != expected[path.name]:
            return fail(f"checksum mismatch: {path.name}")

    try:
        payload = load_json(inventory)
    except StrictJSONError as exc:
        return fail(str(exc))
    if not isinstance(payload, dict):
        return fail("history inventory must contain a JSON object")
    if payload.get("schema_version") != 2:
        return fail("unsupported history inventory schema")
    if payload.get("status") != "verified_history_backup_no_byte_reproducibility_claim":
        return fail("history inventory status overclaims reproducibility")
    if payload.get("repository") != project["repository"]:
        return fail("history inventory repository does not match project.json")
    if payload.get("version") != project["version"]:
        return fail("history inventory version does not match project.json")
    if payload.get("bundle") != bundle.name or payload.get("bundle_sha256") != sha256_file(bundle):
        return fail("history inventory does not match bundle")
    head_commit = payload.get("head_commit")
    if not isinstance(head_commit, str) or OID_RE.fullmatch(head_commit) is None:
        return fail("history inventory has an invalid head_commit")
    if payload.get("temporary_recovery_ref") != TEMP_REF:
        return fail("history inventory temporary recovery ref drift")
    try:
        recorded_heads = validate_inventory_heads(payload)
    except IntegrityError as exc:
        return fail(str(exc))
    recorded_map = {entry["ref"]: entry["oid"] for entry in recorded_heads}
    if recorded_map.get("HEAD") != head_commit:
        return fail("history inventory HEAD does not match head_commit")
    if recorded_map.get(TEMP_REF) != head_commit:
        return fail("history inventory omits the exact detached-HEAD recovery ref")
    head_ref = payload.get("head_ref")
    if head_ref != "DETACHED":
        if not isinstance(head_ref, str) or not head_ref.startswith("refs/"):
            return fail("history inventory has an invalid head_ref")
        if recorded_map.get(head_ref) != head_commit:
            return fail("history inventory head_ref does not identify head_commit")

    try:
        completed = subprocess.run(
            ["git", "bundle", "verify", str(bundle)],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        listed = subprocess.run(
            ["git", "bundle", "list-heads", str(bundle)],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return fail("git executable is unavailable")
    if completed.returncode != 0:
        return fail(f"git bundle verify failed:\n{completed.stdout}{completed.stderr}")
    if listed.returncode != 0:
        return fail(f"git bundle list-heads failed:\n{listed.stdout}{listed.stderr}")
    try:
        actual_heads = parse_bundle_heads(listed.stdout)
    except ValueError as exc:
        return fail(str(exc))
    if actual_heads != recorded_heads:
        return fail("history inventory does not exactly match git bundle list-heads")

    print(
        f"history bundle verification passed: head={head_commit}, "
        f"heads={len(recorded_heads)}, sha256={payload['bundle_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
