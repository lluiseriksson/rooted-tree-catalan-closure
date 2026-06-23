#!/usr/bin/env python3
"""Verify a Git history bundle, its ref inventory, and SHA-256 checksums."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fail(message: str) -> int:
    print(f"ERROR: {message}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--release-dir", default="history-release")
    args = parser.parse_args()

    root = args.repository.resolve()
    project_path = root / "project.json"
    if not project_path.is_file():
        return fail(f"missing project metadata: {project_path}")
    project = json.loads(project_path.read_text(encoding="utf-8"))
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

    expected: dict[str, str] = {}
    for line in sums.read_text(encoding="utf-8").splitlines():
        try:
            digest, name = line.split("  ", 1)
        except ValueError:
            return fail(f"malformed checksum line: {line!r}")
        if name in expected:
            return fail(f"duplicate checksum entry: {name}")
        if not (len(digest) == 64 and all(char in "0123456789abcdef" for char in digest)):
            return fail(f"invalid SHA-256 digest for {name}")
        expected[name] = digest
    if set(expected) != {bundle.name, inventory.name}:
        return fail("history checksum inventory has unexpected files")
    for path in (bundle, inventory):
        if sha256(path) != expected[path.name]:
            return fail(f"checksum mismatch: {path.name}")

    payload = json.loads(inventory.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        return fail("unsupported history inventory schema")
    if payload.get("status") != "verified_history_backup_no_byte_reproducibility_claim":
        return fail("history inventory status overclaims reproducibility")
    if payload.get("repository") != project["repository"]:
        return fail("history inventory repository does not match project.json")
    if payload.get("version") != project["version"]:
        return fail("history inventory version does not match project.json")
    if payload.get("bundle") != bundle.name or payload.get("bundle_sha256") != sha256(bundle):
        return fail("history inventory does not match bundle")
    refs = payload.get("refs")
    if not isinstance(refs, list) or not refs:
        return fail("history inventory contains no refs")
    if not all(
        isinstance(item, dict)
        and isinstance(item.get("ref"), str)
        and isinstance(item.get("commit"), str)
        and len(item["commit"]) == 40
        for item in refs
    ):
        return fail("history inventory has malformed refs")
    if not any(item.get("commit") == payload.get("head_commit") for item in refs):
        return fail("history inventory does not retain the recorded HEAD commit")
    if not any(item.get("ref") == payload.get("temporary_recovery_ref") for item in refs):
        return fail("history inventory omits the detached-HEAD recovery ref")
    try:
        completed = subprocess.run(
            ["git", "bundle", "verify", str(bundle)],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return fail("git executable is unavailable")
    if completed.returncode != 0:
        return fail(f"git bundle verify failed:\n{completed.stdout}{completed.stderr}")
    print(
        f"history bundle verification passed: head={payload['head_commit']}, "
        f"refs={len(refs)}, sha256={payload['bundle_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
