#!/usr/bin/env python3
"""Require a source release repackaged after extraction to be byte-identical."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from release_integrity import (
    IntegrityError,
    archive_members,
    safe_extract_members,
    validate_archive_resource_limits,
    validate_zip_info,
)
from strict_json import load_canonical as load_json

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str], cwd: Path) -> None:
    completed = subprocess.run(command, cwd=cwd, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed with status {completed.returncode}: {' '.join(command)}")


def snapshot(directory: Path) -> dict[str, bytes]:
    return {
        path.name: path.read_bytes()
        for path in sorted(directory.iterdir())
        if path.is_file()
    }


def main() -> int:
    project = load_json(ROOT / "project.json")
    if not isinstance(project, dict):
        raise SystemExit("project.json must contain a JSON object")
    prefix = f"rooted-tree-catalan-closure-v{project['version']}"
    release_date = datetime.fromisoformat(project["release_date"])
    timestamp = (release_date.year, release_date.month, release_date.day, 0, 0, 0)

    try:
        with tempfile.TemporaryDirectory(prefix="rtcc-repackage-") as temp:
            work = Path(temp)
            first = work / "first"
            extraction = work / "extracted"
            second = work / "second"
            first.mkdir()
            extraction.mkdir()
            second.mkdir()

            run([sys.executable, "scripts/package_release.py", "--output-dir", str(first)], ROOT)
            run([sys.executable, "scripts/verify_release.py", "--release-dir", str(first)], ROOT)

            source_archive = first / f"{prefix}.zip"
            with zipfile.ZipFile(source_archive) as archive:
                infos = archive.infolist()
                validate_archive_resource_limits(infos)
                members = archive_members(infos, prefix)
                for info in infos:
                    validate_zip_info(info, timestamp)
                extracted_root = safe_extract_members(archive, members, extraction, prefix)

            run([sys.executable, "scripts/check_source_manifest.py"], extracted_root)
            run(
                [sys.executable, "scripts/package_release.py", "--output-dir", str(second)],
                extracted_root,
            )
            run(
                [sys.executable, "scripts/verify_release.py", "--release-dir", str(second)],
                extracted_root,
            )

            first_snapshot = snapshot(first)
            second_snapshot = snapshot(second)
            if first_snapshot.keys() != second_snapshot.keys():
                raise RuntimeError("repackaged release output file sets differ")
            changed = [
                name
                for name in first_snapshot
                if first_snapshot[name] != second_snapshot[name]
            ]
            if changed:
                raise RuntimeError(
                    "repackaged release is not byte-identical: " + ", ".join(changed)
                )
    except (OSError, RuntimeError, zipfile.BadZipFile, IntegrityError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(
        "source repackaging passed: extracted release reproduces ZIP, sidecar, SPDX SBOM, "
        "release metadata, and complete SHA256SUMS byte for byte"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
