#!/usr/bin/env python3
"""Strict, reusable validators for source manifests and portable ZIP releases."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import unicodedata
import zipfile
from pathlib import Path
from typing import Iterable, Sequence

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MANIFEST_LINE_RE = re.compile(r"^([0-9a-f]{64})  (.+)$")
WINDOWS_FORBIDDEN = set('<>:"|?*')
WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "CLOCK$",
    "CONIN$",
    "CONOUT$",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
MAX_COMPONENT_UTF8_BYTES = 255
MAX_RELATIVE_PATH_UTF8_BYTES = 4096
MAX_ARCHIVE_FILES = 10_000
MAX_ARCHIVE_FILE_BYTES = 128 * 1024 * 1024
MAX_ARCHIVE_TOTAL_BYTES = 512 * 1024 * 1024
FORBIDDEN_UNICODE_CATEGORIES = {"Cc", "Cf", "Cs", "Zl", "Zp"}


class IntegrityError(ValueError):
    """Raised when a release artifact violates the canonical integrity policy."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Return a streaming SHA-256 digest for a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_portable_relative_path(path: str) -> str:
    """Validate a canonical, cross-platform relative source path."""
    if not path:
        raise IntegrityError("empty source path")
    if path.startswith("/") or "\\" in path:
        raise IntegrityError(f"non-POSIX or absolute source path: {path!r}")
    if any(unicodedata.category(char) in FORBIDDEN_UNICODE_CATEGORIES for char in path):
        raise IntegrityError(f"control, formatting, or line-separator character in source path: {path!r}")
    if path != unicodedata.normalize("NFC", path):
        raise IntegrityError(f"source path is not Unicode NFC-normalized: {path!r}")
    try:
        encoded = path.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise IntegrityError(f"source path is not valid Unicode: {path!r}") from exc
    if len(encoded) > MAX_RELATIVE_PATH_UTF8_BYTES:
        raise IntegrityError(f"source path is unreasonably long: {path!r}")
    parts = path.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise IntegrityError(f"noncanonical source path: {path!r}")
    for part in parts:
        if len(part.encode("utf-8")) > MAX_COMPONENT_UTF8_BYTES:
            raise IntegrityError(f"source path component exceeds 255 UTF-8 bytes: {path!r}")
        if any(char in WINDOWS_FORBIDDEN for char in part):
            raise IntegrityError(f"Windows-incompatible source path: {path!r}")
        if part.endswith((" ", ".")):
            raise IntegrityError(f"source path has a nonportable trailing character: {path!r}")
        stem = part.split(".", 1)[0].upper()
        if stem in WINDOWS_RESERVED:
            raise IntegrityError(f"Windows-reserved source path: {path!r}")
    return path


def portable_path_key(path: str) -> str:
    """Return the case- and normalization-insensitive collision key for a valid path."""
    validate_portable_relative_path(path)
    return unicodedata.normalize("NFC", path).casefold()


def _reject_path_collisions(paths: Iterable[str]) -> None:
    exact: set[str] = set()
    folded: dict[str, str] = {}
    for path in paths:
        validate_portable_relative_path(path)
        if path in exact:
            raise IntegrityError(f"duplicate source path: {path}")
        exact.add(path)
        key = portable_path_key(path)
        previous = folded.get(key)
        if previous is not None and previous != path:
            raise IntegrityError(f"case-insensitive path collision: {previous!r} and {path!r}")
        folded[key] = path


def format_source_manifest(records: Sequence[tuple[str, str]]) -> bytes:
    """Return a normalized SHA-256 manifest sorted by source path."""
    ordered = sorted(records, key=lambda item: item[0])
    _reject_path_collisions(path for path, _ in ordered)
    for path, digest in ordered:
        if SHA256_RE.fullmatch(digest) is None:
            raise IntegrityError(f"invalid SHA-256 digest for {path}: {digest!r}")
    return "".join(f"{digest}  {path}\n" for path, digest in ordered).encode("utf-8")


def parse_source_manifest(text: str) -> dict[str, str]:
    """Parse and strictly validate a normalized SHA-256 source manifest."""
    if not text:
        raise IntegrityError("source manifest is empty")
    if not text.endswith("\n"):
        raise IntegrityError("source manifest lacks its final newline")
    records: dict[str, str] = {}
    folded: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        match = MANIFEST_LINE_RE.fullmatch(line)
        if match is None:
            raise IntegrityError(f"malformed source-manifest line {line_number}")
        digest, path = match.groups()
        validate_portable_relative_path(path)
        if path in records:
            raise IntegrityError(f"duplicate path in source manifest: {path}")
        key = portable_path_key(path)
        previous = folded.get(key)
        if previous is not None and previous != path:
            raise IntegrityError(
                f"case-insensitive path collision in source manifest: {previous!r} and {path!r}"
            )
        records[path] = digest
        folded[key] = path
    if list(records) != sorted(records):
        raise IntegrityError("source-manifest paths are not in canonical order")
    return records


def archive_members(
    infos: Sequence[zipfile.ZipInfo],
    prefix: str,
) -> dict[str, zipfile.ZipInfo]:
    """Validate ZIP member names and map canonical relative paths to entries."""
    validate_portable_relative_path(prefix)
    if "/" in prefix:
        raise IntegrityError("archive prefix must be one path component")
    expected_prefix = prefix + "/"
    names = [info.filename for info in infos]
    if len(names) != len(set(names)):
        raise IntegrityError("ZIP contains duplicate names")
    folded: dict[str, str] = {}
    members: dict[str, zipfile.ZipInfo] = {}
    for info in infos:
        name = info.filename
        if not name.startswith(expected_prefix):
            raise IntegrityError(f"ZIP entry escapes the expected top-level directory: {name!r}")
        relative = name[len(expected_prefix) :]
        validate_portable_relative_path(relative)
        key = portable_path_key(name)
        previous = folded.get(key)
        if previous is not None and previous != name:
            raise IntegrityError(f"case-insensitive ZIP collision: {previous!r} and {name!r}")
        if info.is_dir():
            raise IntegrityError(f"ZIP contains an explicit directory entry: {name}")
        folded[key] = name
        members[relative] = info
    return members


def validate_source_payload_limits(
    file_sizes: Sequence[tuple[str, int]],
    manifest_size: int,
) -> tuple[int, int]:
    """Fail before writing when producer inputs exceed the verifier's archive ceilings."""
    entry_count = len(file_sizes) + 1  # SOURCE-MANIFEST.sha256 is also archived.
    if entry_count > MAX_ARCHIVE_FILES:
        raise IntegrityError(
            f"source package would contain too many entries: {entry_count} > {MAX_ARCHIVE_FILES}"
        )
    total = 0
    for path, size in file_sizes:
        validate_portable_relative_path(path)
        if not isinstance(size, int) or size < 0:
            raise IntegrityError(f"source file has an invalid size: {path}: {size!r}")
        if size > MAX_ARCHIVE_FILE_BYTES:
            raise IntegrityError(f"source file is too large: {path}: {size} bytes")
        total += size
    if manifest_size < 0 or manifest_size > MAX_ARCHIVE_FILE_BYTES:
        raise IntegrityError(f"source manifest is too large: {manifest_size} bytes")
    total += manifest_size
    if total > MAX_ARCHIVE_TOTAL_BYTES:
        raise IntegrityError(f"source package would expand beyond the limit: {total} bytes")
    return entry_count, total


def validate_archive_resource_limits(infos: Sequence[zipfile.ZipInfo]) -> tuple[int, int]:
    """Reject source archives with implausible file counts or expanded sizes."""
    if len(infos) > MAX_ARCHIVE_FILES:
        raise IntegrityError(f"ZIP has too many entries: {len(infos)} > {MAX_ARCHIVE_FILES}")
    total = 0
    for info in infos:
        if info.file_size < 0 or info.compress_size < 0:
            raise IntegrityError(f"ZIP entry has a negative size: {info.filename}")
        if info.file_size > MAX_ARCHIVE_FILE_BYTES:
            raise IntegrityError(
                f"ZIP entry is too large: {info.filename}: {info.file_size} bytes"
            )
        total += info.file_size
        if total > MAX_ARCHIVE_TOTAL_BYTES:
            raise IntegrityError(
                f"ZIP expands beyond the source-archive limit: {total} bytes"
            )
    return len(infos), total


def validate_zip_info(
    info: zipfile.ZipInfo,
    expected_timestamp: tuple[int, int, int, int, int, int],
) -> int:
    """Validate normalized metadata and return the portable permission mode."""
    if info.compress_type != zipfile.ZIP_STORED:
        raise IntegrityError(f"ZIP entry is compressed: {info.filename}")
    if info.file_size != info.compress_size:
        raise IntegrityError(f"stored ZIP entry size mismatch: {info.filename}")
    if info.date_time != expected_timestamp:
        raise IntegrityError(f"ZIP timestamp drift: {info.filename}: {info.date_time}")
    if info.create_system != 3:
        raise IntegrityError(f"ZIP entry is not normalized as Unix: {info.filename}")
    if info.create_version != 20 or info.extract_version != 20:
        raise IntegrityError(f"ZIP entry has noncanonical version metadata: {info.filename}")
    raw_mode = info.external_attr >> 16
    if not stat.S_ISREG(raw_mode):
        raise IntegrityError(f"ZIP entry is not marked as a regular Unix file: {info.filename}")
    permissions = stat.S_IMODE(raw_mode)
    if permissions not in {0o644, 0o755} or raw_mode != stat.S_IFREG | permissions:
        raise IntegrityError(
            f"unexpected ZIP Unix mode {oct(raw_mode)}: {info.filename}"
        )
    if info.external_attr & 0xFFFF:
        raise IntegrityError(
            f"unexpected ZIP DOS attributes {hex(info.external_attr & 0xFFFF)}: {info.filename}"
        )
    try:
        info.filename.encode("ascii")
        expected_utf8_flag = 0
    except UnicodeEncodeError:
        expected_utf8_flag = 0x800
    if info.flag_bits != expected_utf8_flag:
        raise IntegrityError(
            f"ZIP UTF-8 flag policy mismatch {hex(info.flag_bits)}: {info.filename}"
        )
    if info.extra:
        raise IntegrityError(f"ZIP entry contains noncanonical extra metadata: {info.filename}")
    if info.comment:
        raise IntegrityError(f"ZIP entry contains a comment: {info.filename}")
    if info.internal_attr != 0 or info.volume != 0:
        raise IntegrityError(f"ZIP entry contains noncanonical internal metadata: {info.filename}")
    return permissions


def safe_extract_members(
    source_zip: zipfile.ZipFile,
    members: dict[str, zipfile.ZipInfo],
    extraction_root: Path,
    prefix: str,
) -> Path:
    """Extract validated regular files without trusting host permission semantics.

    Unix modes are restored on POSIX.  Windows extraction deliberately leaves host modes
    alone; integrity is established from the ZIP metadata before extraction, which avoids
    false failures caused by Windows' limited executable-bit model.
    """
    destination = extraction_root / prefix
    destination.mkdir(parents=True, exist_ok=False)
    for relative, info in members.items():
        target = destination.joinpath(*relative.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        with source_zip.open(info, "r") as source, target.open("xb") as output:
            shutil.copyfileobj(source, output)
        if os.name != "nt":
            target.chmod(stat.S_IMODE(info.external_attr >> 16))
    return destination


def compare_manifest_to_files(
    records: dict[str, str],
    root: Path,
    files: Sequence[Path],
) -> list[str]:
    """Return deterministic diagnostics for manifest/file inventory differences."""
    current = {
        path.relative_to(root).as_posix(): sha256(path.read_bytes())
        for path in files
    }
    errors: list[str] = []
    missing = sorted(set(records) - set(current))
    extra = sorted(set(current) - set(records))
    changed = sorted(
        path for path in set(records) & set(current) if records[path] != current[path]
    )
    if missing:
        errors.append("manifest paths missing from source tree: " + ", ".join(missing))
    if extra:
        errors.append("source-tree paths missing from manifest: " + ", ".join(extra))
    if changed:
        errors.append("source files with checksum drift: " + ", ".join(changed))
    return errors
