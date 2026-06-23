#!/usr/bin/env python3
"""Create and deeply verify a Git bundle preserving repository history and refs.

The deterministic source ZIP restores the publication tree. This complementary Git
bundle restores commits and refs. It is checksummed and subjected to bundle verification,
an exact head inventory, a mirror restore, strict full-object fsck, and release-tag binding.
It is deliberately not claimed to be byte-identical across Git versions.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from history_integrity import (
    TEMP_REF,
    HistoryIntegrityError,
    deep_verify_bundle,
    parse_bundle_heads,
    validate_oid,
)
from release_integrity import sha256_file
from strict_json import StrictJSONError, canonical_dumps, load_canonical as load_json

DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def run(root: Path, *args: str, capture: bool = True) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=capture,
    )
    return completed.stdout.strip() if capture else ""


def reject_irregular_outputs(paths: list[Path]) -> None:
    """Reject output symlinks/directories before any history artifact is written."""
    for path in paths:
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise HistoryIntegrityError(f"refusing non-regular history output: {path}")


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
        object_format = run(root, "rev-parse", "--show-object-format")
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
    version = project.get("version")
    if not isinstance(version, str):
        print("ERROR: project.json version must be a string", file=sys.stderr)
        return 1
    prefix = f"rooted-tree-catalan-closure-v{version}"
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    output_dir = output_dir.resolve()
    if output_dir.is_symlink() or (output_dir.exists() and not output_dir.is_dir()):
        print(f"ERROR: invalid history output directory: {output_dir}", file=sys.stderr)
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = output_dir / f"{prefix}-history.bundle"
    inventory = output_dir / f"{prefix}.history.json"
    sums = output_dir / f"{prefix}.history.SHA256SUMS"
    try:
        reject_irregular_outputs([bundle, inventory, sums])
    except HistoryIntegrityError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    try:
        head_commit = validate_oid(run(root, "rev-parse", "HEAD"), object_format, label="HEAD")
    except (subprocess.CalledProcessError, HistoryIntegrityError) as exc:
        print(f"ERROR: cannot resolve repository HEAD: {exc}", file=sys.stderr)
        return 1
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
        bundle_heads = parse_bundle_heads(
            run(root, "bundle", "list-heads", str(bundle)), object_format
        )
        restoration = deep_verify_bundle(
            bundle,
            bundle_heads,
            head_commit=head_commit,
            object_format=object_format,
            version=version,
        )
    except (subprocess.CalledProcessError, HistoryIntegrityError) as exc:
        print(f"ERROR: cannot create or deeply verify Git bundle: {exc}", file=sys.stderr)
        return 1
    finally:
        subprocess.run(["git", "update-ref", "-d", TEMP_REF], cwd=root, check=False)

    bundle_digest = sha256_file(bundle)
    payload = {
        "schema_version": 3,
        "status": "verified_history_backup_no_byte_reproducibility_claim",
        "repository": project["repository"],
        "version": version,
        "object_format": object_format,
        "head_commit": head_commit,
        "head_ref": head_ref,
        "temporary_recovery_ref": TEMP_REF,
        "release_tag": restoration.release_tag,
        "release_tag_object": restoration.release_tag_object,
        "release_tag_commit": restoration.release_tag_commit,
        "release_tag_annotated": restoration.release_tag_annotated,
        "bundle": bundle.name,
        "bundle_sha256": bundle_digest,
        "bundle_heads": bundle_heads,
        "git_bundle_verify": (verify.stdout + verify.stderr).splitlines(),
        "restoration_verification": {
            "mirror_clone": True,
            "exact_refs": True,
            "restored_ref_count": restoration.restored_ref_count,
            "git_fsck_full_strict": restoration.fsck_full_strict,
        },
        "restore": [
            f"git clone {bundle.name} rooted-tree-catalan-closure",
            "cd rooted-tree-catalan-closure",
            f"git checkout {head_commit}",
            "git fsck --full --strict",
        ],
    }
    inventory.write_text(
        canonical_dumps(payload),
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
