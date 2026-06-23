#!/usr/bin/env python3
"""Reusable deep-integrity checks for Git history recovery bundles."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

OBJECT_ID_LENGTHS = {"sha1": 40, "sha256": 64}
TEMP_REF = "refs/rtc-recovery/HEAD"


class HistoryIntegrityError(ValueError):
    """Raised when a Git bundle cannot restore the advertised repository state."""


@dataclass(frozen=True)
class BundleRestorationReport:
    object_format: str
    restored_head: str
    restored_ref_count: int
    release_tag: str
    release_tag_object: str
    release_tag_commit: str
    release_tag_annotated: bool
    fsck_full_strict: bool


def oid_pattern(object_format: str) -> re.Pattern[str]:
    """Return the exact lowercase object-ID pattern for one Git object format."""
    length = OBJECT_ID_LENGTHS.get(object_format)
    if length is None:
        raise HistoryIntegrityError(f"unsupported Git object format: {object_format!r}")
    return re.compile(rf"^[0-9a-f]{{{length}}}$")


def validate_oid(value: str, object_format: str, *, label: str = "object id") -> str:
    """Validate and return one lowercase Git object ID."""
    if oid_pattern(object_format).fullmatch(value) is None:
        raise HistoryIntegrityError(f"invalid {object_format} {label}: {value!r}")
    return value


def parse_bundle_heads(text: str, object_format: str) -> list[dict[str, str]]:
    """Parse ``git bundle list-heads`` output into a canonical exact inventory."""
    heads: list[dict[str, str]] = []
    seen: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), 1):
        try:
            oid, ref = line.split(" ", 1)
        except ValueError as exc:
            raise HistoryIntegrityError(
                f"malformed git bundle head line {line_number}: {line!r}"
            ) from exc
        validate_oid(oid, object_format, label=f"bundle head on line {line_number}")
        if ref != "HEAD" and not ref.startswith("refs/"):
            raise HistoryIntegrityError(
                f"noncanonical git bundle head on line {line_number}: {ref!r}"
            )
        if not ref or ref in seen:
            raise HistoryIntegrityError(f"duplicate or empty git bundle head: {ref!r}")
        seen.add(ref)
        heads.append({"ref": ref, "oid": oid})
    if not heads:
        raise HistoryIntegrityError("git bundle advertises no heads")
    heads.sort(key=lambda item: item["ref"])
    return heads


def parse_show_ref(text: str, object_format: str) -> dict[str, str]:
    """Parse canonical ``for-each-ref`` output without silently overwriting refs."""
    refs: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        try:
            oid, ref = line.split(" ", 1)
        except ValueError as exc:
            raise HistoryIntegrityError(
                f"malformed restored-ref line {line_number}: {line!r}"
            ) from exc
        validate_oid(oid, object_format, label=f"restored ref on line {line_number}")
        if not ref.startswith("refs/") or ref in refs:
            raise HistoryIntegrityError(f"duplicate or noncanonical restored ref: {ref!r}")
        refs[ref] = oid
    return dict(sorted(refs.items()))


def _run_git(
    args: Iterable[str],
    *,
    cwd: Path | None = None,
    git_dir: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = ["git"]
    if git_dir is not None:
        command.extend(["--git-dir", str(git_dir)])
    command.extend(args)
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise HistoryIntegrityError("git executable is unavailable") from exc


def deep_verify_bundle(
    bundle: Path,
    expected_heads: list[dict[str, str]],
    *,
    head_commit: str,
    object_format: str,
    version: str,
) -> BundleRestorationReport:
    """Clone a bundle, run strict object checks, and verify exact restored refs/tag binding."""
    validate_oid(head_commit, object_format, label="head commit")
    expected_map = {entry["ref"]: entry["oid"] for entry in expected_heads}
    if len(expected_map) != len(expected_heads):
        raise HistoryIntegrityError("duplicate refs in expected bundle-head inventory")
    if expected_map.get("HEAD") != head_commit:
        raise HistoryIntegrityError("bundle HEAD does not match the advertised head commit")
    if expected_map.get(TEMP_REF) != head_commit:
        raise HistoryIntegrityError("bundle omits the detached-HEAD recovery ref")

    release_tag = f"refs/tags/v{version}"
    release_tag_object = expected_map.get(release_tag)
    if release_tag_object is None:
        raise HistoryIntegrityError(f"bundle omits required release tag {release_tag}")
    validate_oid(release_tag_object, object_format, label="release-tag object")

    bundle = bundle.resolve()
    if bundle.is_symlink() or not bundle.is_file():
        raise HistoryIntegrityError(f"history bundle is not a regular file: {bundle}")

    with tempfile.TemporaryDirectory(prefix="rtc-bundle-restore-") as temporary:
        temp = Path(temporary)
        mirror = temp / "mirror.git"
        home = temp / "home"
        home.mkdir()
        clean_env = {
            key: value for key, value in os.environ.items() if not key.startswith("GIT_")
        }
        clean_env.update(
            {
                "GIT_ALLOW_PROTOCOL": "file",
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
                "HOME": str(home),
                "LANG": "C",
                "LC_ALL": "C",
                "XDG_CONFIG_HOME": str(home / "xdg"),
            }
        )
        cloned = _run_git(
            ["clone", "--mirror", "--no-local", str(bundle), str(mirror)],
            env=clean_env,
        )
        if cloned.returncode != 0:
            raise HistoryIntegrityError(
                "cannot restore Git bundle into a mirror clone:\n"
                + cloned.stdout
                + cloned.stderr
            )

        restored_format = _run_git(
            ["rev-parse", "--show-object-format"], git_dir=mirror, env=clean_env
        )
        if restored_format.returncode != 0:
            raise HistoryIntegrityError(
                "cannot determine restored Git object format:\n"
                + restored_format.stdout
                + restored_format.stderr
            )
        actual_format = restored_format.stdout.strip()
        if actual_format != object_format:
            raise HistoryIntegrityError(
                f"restored Git object format {actual_format!r} != {object_format!r}"
            )

        fsck = _run_git(
            ["fsck", "--full", "--strict", "--no-reflogs", "--no-dangling", "--no-progress"],
            git_dir=mirror,
            env=clean_env,
        )
        if fsck.returncode != 0:
            raise HistoryIntegrityError(
                "restored Git bundle failed git fsck --full --strict:\n"
                + fsck.stdout
                + fsck.stderr
            )

        restored_head_proc = _run_git(["rev-parse", "HEAD"], git_dir=mirror, env=clean_env)
        if restored_head_proc.returncode != 0:
            raise HistoryIntegrityError(
                "restored Git bundle has no resolvable HEAD:\n"
                + restored_head_proc.stdout
                + restored_head_proc.stderr
            )
        restored_head = restored_head_proc.stdout.strip()
        validate_oid(restored_head, object_format, label="restored HEAD")
        if restored_head != head_commit:
            raise HistoryIntegrityError(
                f"restored HEAD {restored_head} does not match {head_commit}"
            )

        refs_proc = _run_git(
            ["for-each-ref", "--format=%(objectname) %(refname)"],
            git_dir=mirror,
            env=clean_env,
        )
        if refs_proc.returncode != 0:
            raise HistoryIntegrityError(
                "cannot inventory restored Git refs:\n" + refs_proc.stdout + refs_proc.stderr
            )
        actual_refs = parse_show_ref(refs_proc.stdout, object_format)
        expected_refs = dict(
            sorted((ref, oid) for ref, oid in expected_map.items() if ref != "HEAD")
        )
        if actual_refs != expected_refs:
            missing = sorted(set(expected_refs) - set(actual_refs))
            extra = sorted(set(actual_refs) - set(expected_refs))
            changed = sorted(
                ref
                for ref in set(expected_refs) & set(actual_refs)
                if expected_refs[ref] != actual_refs[ref]
            )
            raise HistoryIntegrityError(
                "restored Git refs do not exactly match bundle heads; "
                f"missing={missing}, extra={extra}, changed={changed}"
            )

        tag_type = _run_git(["cat-file", "-t", release_tag], git_dir=mirror, env=clean_env)
        if tag_type.returncode != 0 or tag_type.stdout.strip() != "tag":
            raise HistoryIntegrityError(f"release tag {release_tag} is not an annotated tag")
        peeled = _run_git(
            ["rev-parse", f"{release_tag}^{{commit}}"], git_dir=mirror, env=clean_env
        )
        if peeled.returncode != 0:
            raise HistoryIntegrityError(
                f"cannot peel release tag {release_tag} to a commit:\n"
                + peeled.stdout
                + peeled.stderr
            )
        release_tag_commit = peeled.stdout.strip()
        validate_oid(release_tag_commit, object_format, label="peeled release-tag commit")
        if release_tag_commit != head_commit:
            raise HistoryIntegrityError(
                f"release tag {release_tag} peels to {release_tag_commit}, expected {head_commit}"
            )

    return BundleRestorationReport(
        object_format=object_format,
        restored_head=head_commit,
        restored_ref_count=len(expected_map) - 1,
        release_tag=release_tag,
        release_tag_object=release_tag_object,
        release_tag_commit=head_commit,
        release_tag_annotated=True,
        fsck_full_strict=True,
    )
