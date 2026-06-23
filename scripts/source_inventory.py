#!/usr/bin/env python3
"""Discover the canonical source-file inventory used by release tooling."""

from __future__ import annotations

import subprocess
from pathlib import Path, PurePosixPath

EXCLUDED_PARTS = {
    ".git",
    "release",
    "history-release",
    "build",
    ".work",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    ".tox",
    ".nox",
    ".hypothesis",
    "htmlcov",
}
EXCLUDED_SUFFIXES = {".aux", ".fdb_latexmk", ".fls", ".out", ".synctex.gz", ".toc"}
EXCLUDED_NAMES = {
    "SOURCE-MANIFEST.sha256",
    "main.pdf",
    "main.log",
    ".coverage",
    ".DS_Store",
    "Thumbs.db",
    "replay-build.log",
    "replay-oracle.log",
    "replay-report.json",
}


class SourceInventoryError(RuntimeError):
    """Raised when a Git checkout cannot be inventoried safely."""


def source_exclusion_reason(relative: str) -> str | None:
    """Return why a canonical relative path is excluded from source releases."""
    parts = PurePosixPath(relative).parts
    if any(part in EXCLUDED_PARTS for part in parts):
        return "path contains an excluded generated or repository-internal directory"
    name = parts[-1] if parts else ""
    if name in EXCLUDED_NAMES:
        return "path has an excluded generated filename"
    if any(name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES):
        return "path has an excluded generated suffix"
    return None


def git_worktree_status(root: Path) -> bytes | None:
    """Return porcelain status bytes, or ``None`` when ``root`` is not a checkout.

    A present ``.git`` entry is treated as an assertion that Git inventory must work.
    Falling back to a recursive filesystem scan in a broken checkout could accidentally
    package ignored, untracked, or repository-internal files, so Git failures are fatal.
    """
    root = root.resolve()
    if not (root / ".git").exists():
        return None
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SourceInventoryError("Git checkout found but git executable is unavailable") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise SourceInventoryError(f"cannot inspect Git worktree status: {detail or 'git status failed'}")
    return completed.stdout


def _git_candidates(root: Path) -> list[Path] | None:
    """Return tracked files only, or ``None`` outside a Git checkout."""
    if not (root / ".git").exists():
        return None
    try:
        completed = subprocess.run(
            ["git", "ls-files", "--cached", "-z"],
            cwd=root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        raise SourceInventoryError("Git checkout found but git executable is unavailable") from exc
    if completed.returncode != 0:
        detail = completed.stderr.decode("utf-8", errors="replace").strip()
        raise SourceInventoryError(f"cannot enumerate tracked Git files: {detail or 'git ls-files failed'}")
    try:
        names = [item.decode("utf-8") for item in completed.stdout.split(b"\0") if item]
    except UnicodeDecodeError as exc:
        raise SourceInventoryError("tracked Git path is not valid UTF-8") from exc
    return [root / name for name in names]


def repository_files(root: Path, output_dir: Path | None = None) -> list[Path]:
    """Return distributable source files in canonical POSIX path order.

    A Git checkout contributes tracked files only. This prevents an untracked credential,
    scratch file, or ignored build product from silently entering a release. An extracted
    source archive has no ``.git`` entry, so it is scanned recursively with the identical
    exclusion policy. Generated ``SOURCE-MANIFEST.sha256`` files are deliberately excluded
    so a source release can be repackaged without producing a duplicate manifest entry.
    """
    root = root.resolve()
    resolved_output = output_dir.resolve() if output_dir is not None else None
    candidates = _git_candidates(root)
    from_git = candidates is not None
    if candidates is None:
        candidates = [path for path in root.rglob("*") if path.is_file()]

    selected: list[Path] = []
    for path in candidates:
        if path.is_symlink():
            if from_git:
                relative = path.relative_to(root).as_posix()
                raise SourceInventoryError(
                    f"tracked symbolic links are not supported in source releases: {relative}"
                )
            continue
        if not path.is_file():
            if from_git:
                relative = path.relative_to(root).as_posix()
                raise SourceInventoryError(
                    f"tracked path is missing or is not a regular file: {relative}"
                )
            continue
        resolved = path.resolve()
        if resolved_output is not None:
            try:
                resolved.relative_to(resolved_output)
            except ValueError:
                pass
            else:
                continue
        try:
            rel = resolved.relative_to(root)
        except ValueError:
            continue
        if source_exclusion_reason(rel.as_posix()) is not None:
            continue
        selected.append(path)
    return sorted(selected, key=lambda path: path.relative_to(root).as_posix())
