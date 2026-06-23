#!/usr/bin/env python3
"""Discover the canonical source-file inventory used by release tooling."""

from __future__ import annotations

import subprocess
from pathlib import Path

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


def _git_candidates(root: Path) -> list[Path] | None:
    """Return tracked and non-ignored files, or ``None`` outside a usable checkout."""
    if not (root / ".git").exists():
        return None
    try:
        raw = subprocess.check_output(
            ["git", "ls-files", "-co", "--exclude-standard", "-z"],
            cwd=root,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return [root / item.decode("utf-8") for item in raw.split(b"\0") if item]


def repository_files(root: Path, output_dir: Path | None = None) -> list[Path]:
    """Return distributable source files in canonical POSIX path order.

    The same filters are used in a Git checkout and in an extracted source archive.
    Generated ``SOURCE-MANIFEST.sha256`` files are deliberately excluded so a source
    release can be repackaged without producing a duplicate manifest entry.
    """
    root = root.resolve()
    resolved_output = output_dir.resolve() if output_dir is not None else None
    candidates = _git_candidates(root)
    if candidates is None:
        candidates = [path for path in root.rglob("*") if path.is_file()]

    selected: list[Path] = []
    for path in candidates:
        if not path.is_file() or path.is_symlink():
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
        if any(part in EXCLUDED_PARTS for part in rel.parts):
            continue
        if path.name in EXCLUDED_NAMES or any(path.name.endswith(suffix) for suffix in EXCLUDED_SUFFIXES):
            continue
        selected.append(path)
    return sorted(selected, key=lambda path: path.relative_to(root).as_posix())
