#!/usr/bin/env python3
"""Create a checksum-verifiable Git bundle preserving repository history and refs.

The deterministic source ZIP restores the publication tree. This complementary Git
bundle restores commit history and refs. A Git bundle is verified structurally and by
SHA-256, but is deliberately not claimed to be byte-identical across Git versions.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from release_integrity import sha256_file
from strict_json import StrictJSONError, load as load_json

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
TEMP_REF = "refs/rtc-recovery/HEAD"
OID_RE = re.compile(r"^[0-9a-f]{40}$")


def run(root: Path, *args: str, capture: bool = True) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=capture,
    )
    return completed.stdout.strip() if capture else ""


def parse_bundle_heads(text: str) -> list[dict[str, str]]:
    """Parse ``git bundle list-heads`` output into a canonical inventory."""
    heads: list[dict[str, str]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), 1):
        try:
            oid, ref = line.split(" ", 1)
        except ValueError as exc:
            raise ValueError(f"malformed git bundle head line {line_number}: {line!r}") from exc
        if OID_RE.fullmatch(oid) is None:
            raise ValueError(f"invalid object id in git bundle head line {line_number}")
        if not ref or ref in seen:
            raise ValueError(f"duplicate or empty git bundle head: {ref!r}")
        seen.add(ref)
        heads.append({"ref": ref, "oid": oid})
    heads.sort(key=lambda item: item["ref"])
    return heads


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output-dir", default="history-release")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()

    root = args.repository.resolve()
    try:
        if run(root, "rev-parse", "--is-inside-work-tree") != "true":
            raise RuntimeError("not inside a Git worktree")
        status = run(root, "status", "--porcelain=v1", "--untracked-files=all")
    except (FileNotFoundError, subprocess.CalledProcessError, RuntimeError) as exc:
        print(f"ERROR: cannot inspect Git repository: {exc}", file=sys.stderr)
        return 1
    if status and not args.allow_dirty:
        print("ERROR: refusing to create history bundle from a dirty worktree", file=sys.stderr)
        return 1

    project_path = root / "project.json"
    try:
        project = load_json(project_path)
    except StrictJSONError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if not isinstance(project, dict):
        print(f"ERROR: {project_path} must contain a JSON object", file=sys.stderr)
        return 1
    prefix = f"rooted-tree-catalan-closure-v{project['version']}"
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = output_dir / f"{prefix}-history.bundle"
    inventory = output_dir / f"{prefix}.history.json"
    sums = output_dir / f"{prefix}.history.SHA256SUMS"

    head_commit = run(root, "rev-parse", "HEAD")
    symbolic = subprocess.run(
        ["git", "symbolic-ref", "--quiet", "HEAD"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    head_ref = symbolic.stdout.strip() if symbolic.returncode == 0 else "DETACHED"

    run(root, "update-ref", TEMP_REF, head_commit)
    try:
        run(root, "bundle", "create", str(bundle), "--all")
        verify = subprocess.run(
            ["git", "bundle", "verify", str(bundle)],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        if verify.returncode != 0:
            print(verify.stdout + verify.stderr, file=sys.stderr)
            return 1
        bundle_heads = parse_bundle_heads(run(root, "bundle", "list-heads", str(bundle)))
    except (subprocess.CalledProcessError, ValueError) as exc:
        print(f"ERROR: cannot create or inventory Git bundle: {exc}", file=sys.stderr)
        return 1
    finally:
        subprocess.run(["git", "update-ref", "-d", TEMP_REF], cwd=root, check=False)

    head_map = {entry["ref"]: entry["oid"] for entry in bundle_heads}
    if head_map.get("HEAD") != head_commit or head_map.get(TEMP_REF) != head_commit:
        print("ERROR: Git bundle does not retain HEAD and the temporary recovery ref", file=sys.stderr)
        return 1

    bundle_digest = sha256_file(bundle)
    payload = {
        "schema_version": 2,
        "status": "verified_history_backup_no_byte_reproducibility_claim",
        "repository": project["repository"],
        "version": project["version"],
        "head_commit": head_commit,
        "head_ref": head_ref,
        "temporary_recovery_ref": TEMP_REF,
        "bundle": bundle.name,
        "bundle_sha256": bundle_digest,
        "bundle_heads": bundle_heads,
        "git_bundle_verify": (verify.stdout + verify.stderr).splitlines(),
        "restore": [
            f"git clone {bundle.name} rooted-tree-catalan-closure",
            "cd rooted-tree-catalan-closure",
            f"git checkout {head_commit}",
        ],
    }
    inventory.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    records = sorted(
        [
            (bundle.name, bundle_digest),
            (inventory.name, sha256_file(inventory)),
        ]
    )
    sums.write_text(
        "".join(f"{digest}  {name}\n" for name, digest in records),
        encoding="utf-8",
        newline="\n",
    )
    for path in (bundle, inventory, sums):
        try:
            print(path.relative_to(root))
        except ValueError:
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
