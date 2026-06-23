#!/usr/bin/env python3
"""Create a checksum-verifiable Git bundle preserving repository history and refs.

The deterministic source ZIP restores the publication tree.  This complementary Git
bundle restores commit history and refs.  A Git bundle is verified structurally and by
SHA-256, but is deliberately not claimed to be byte-identical across Git versions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_ROOT = Path(__file__).resolve().parents[1]
TEMP_REF = "refs/rtc-recovery/HEAD"


def run(root: Path, *args: str, capture: bool = True) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=capture,
    )
    return completed.stdout.strip() if capture else ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
    if not project_path.is_file():
        print(f"ERROR: missing project metadata: {project_path}", file=sys.stderr)
        return 1
    project = json.loads(project_path.read_text(encoding="utf-8"))
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

    # Preserve the exact checked-out commit even for a detached CI checkout.  The
    # recovery ref is intentionally included in the bundle inventory and then removed
    # from the source repository.
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
        ref_lines = run(root, "show-ref").splitlines()
    finally:
        subprocess.run(["git", "update-ref", "-d", TEMP_REF], cwd=root, check=False)

    refs = []
    for line in ref_lines:
        commit, ref = line.split(" ", 1)
        refs.append({"ref": ref, "commit": commit})
    refs.sort(key=lambda item: item["ref"])
    bundle_digest = sha256(bundle)
    payload = {
        "schema_version": 1,
        "status": "verified_history_backup_no_byte_reproducibility_claim",
        "repository": project["repository"],
        "version": project["version"],
        "head_commit": head_commit,
        "head_ref": head_ref,
        "temporary_recovery_ref": TEMP_REF,
        "bundle": bundle.name,
        "bundle_sha256": bundle_digest,
        "refs": refs,
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
    lines = [
        f"{bundle_digest}  {bundle.name}",
        f"{sha256(inventory)}  {inventory.name}",
    ]
    sums.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    for path in (bundle, inventory, sums):
        try:
            print(path.relative_to(root))
        except ValueError:
            print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
