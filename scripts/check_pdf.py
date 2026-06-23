#!/usr/bin/env python3
"""Inspect a manuscript PDF for structure, identity, and passive-content safety."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from strict_json import StrictJSONError, load_canonical as load_json

PDF_HEADER_RE = re.compile(rb"^%PDF-(1\.[0-9])(?:\r\n|\n|\r)")
ACTIVE_PDF_TOKENS = (
    b"Encrypt",
    b"JavaScript",
    b"JS",
    b"OpenAction",
    b"AA",
    b"EmbeddedFile",
    b"Filespec",
    b"Launch",
    b"RichMedia",
    b"XFA",
    b"AcroForm",
)
ACTIVE_TOKEN_RE = re.compile(
    rb"/(?:" + b"|".join(re.escape(token) for token in ACTIVE_PDF_TOKENS) + rb")(?![A-Za-z0-9])"
)


class PDFCheckError(ValueError):
    """Raised when a manuscript PDF violates the repository policy."""


def inspect_pdf_bytes(data: bytes, *, minimum_size: int = 50_000) -> dict[str, object]:
    """Perform dependency-free checks for a single passive, non-incremental PDF."""
    header = PDF_HEADER_RE.match(data)
    if header is None:
        raise PDFCheckError("file has no canonical PDF header")
    if len(data) < minimum_size:
        raise PDFCheckError(f"PDF is unexpectedly small: {len(data)} bytes")
    eof_offsets = [match.start() for match in re.finditer(rb"%%EOF", data)]
    if len(eof_offsets) != 1:
        raise PDFCheckError(
            f"PDF must contain exactly one EOF marker, found {len(eof_offsets)}"
        )
    trailing = data[eof_offsets[0] + len(b"%%EOF") :]
    if trailing.strip(b" \t\r\n"):
        raise PDFCheckError("PDF has non-whitespace bytes after its EOF marker")
    startxref_count = len(re.findall(rb"(?m)^startxref\s*$", data))
    if startxref_count != 1:
        raise PDFCheckError(
            f"PDF must contain one xref terminator and no incremental updates, found {startxref_count}"
        )
    active = sorted({match.group(0).decode("ascii") for match in ACTIVE_TOKEN_RE.finditer(data)})
    if active:
        raise PDFCheckError("PDF contains forbidden active-content markers: " + ", ".join(active))
    return {
        "pdf_version": header.group(1).decode("ascii"),
        "size_bytes": len(data),
        "eof_markers": 1,
        "startxref_markers": 1,
        "active_content_markers": [],
    }


def parse_pdfinfo(text: str) -> dict[str, str]:
    """Parse Poppler ``pdfinfo`` output without silent duplicate-field overwrites."""
    fields: dict[str, str] = {}
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        if ":" not in line:
            raise PDFCheckError(f"malformed pdfinfo line {line_number}: {line!r}")
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in fields:
            raise PDFCheckError(f"duplicate or empty pdfinfo field on line {line_number}: {key!r}")
        fields[key] = value
    return fields


def _expectation(project_path: Path) -> dict[str, Any]:
    try:
        project = load_json(project_path)
    except StrictJSONError as exc:
        raise PDFCheckError(str(exc)) from exc
    if not isinstance(project, dict):
        raise PDFCheckError(f"{project_path} must contain a JSON object")
    metadata = project.get("manuscript_pdf")
    if not isinstance(metadata, dict):
        raise PDFCheckError("project.json omits manuscript_pdf expectations")
    return metadata


def validate_pdfinfo(
    fields: dict[str, str],
    expected: dict[str, Any],
    *,
    allowed_pdf_versions: set[str] | None = None,
) -> int:
    """Validate Poppler metadata against the publication contract and return page count."""
    exact = {
        "Title": expected.get("title"),
        "Author": expected.get("author"),
        "Encrypted": "no" if expected.get("encrypted") is False else None,
        "JavaScript": "no" if expected.get("javascript") is False else None,
        "Form": "none" if expected.get("forms") is False else None,
        "Page rot": "0",
    }
    for key, value in exact.items():
        if value is not None and fields.get(key) != str(value):
            raise PDFCheckError(
                f"pdfinfo {key!r} drift: {fields.get(key)!r} != {str(value)!r}"
            )
    if fields.get("Suspects") not in {None, "no"}:
        raise PDFCheckError(f"pdfinfo reports a suspect PDF: {fields.get('Suspects')!r}")
    allowed_versions = allowed_pdf_versions or {str(expected.get("pdf_version"))}
    if fields.get("PDF version") not in allowed_versions:
        raise PDFCheckError(
            f"pdfinfo PDF version drift: {fields.get('PDF version')!r} not in "
            f"{sorted(allowed_versions)!r}"
        )
    raw_pages = fields.get("Pages", "")
    if re.fullmatch(r"[1-9][0-9]*", raw_pages) is None:
        raise PDFCheckError("pdfinfo did not report a positive page count")
    pages = int(raw_pages)
    expected_pages = expected.get("pages")
    if not isinstance(expected_pages, int) or pages != expected_pages:
        raise PDFCheckError(f"PDF page count drift: {pages} != {expected_pages!r}")
    page_size = expected.get("page_size")
    if not isinstance(page_size, str) or f"({page_size})" not in fields.get("Page size", ""):
        raise PDFCheckError(
            f"PDF page-size drift: {fields.get('Page size')!r} does not identify {page_size!r}"
        )
    return pages


def run_checked_tool(command: list[str], label: str) -> str:
    env = os.environ.copy()
    env.update({"LANG": "C", "LC_ALL": "C"})
    proc = subprocess.run(
        command, text=True, capture_output=True, check=False, env=env
    )
    if proc.returncode != 0:
        raise PDFCheckError(f"{label} failed:\n{proc.stdout}{proc.stderr}")
    return proc.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf")
    parser.add_argument("--project", default="project.json")
    parser.add_argument(
        "--expected-text",
        default="Rooted-tree summation and Catalan closure",
        help="text required in the Poppler extraction",
    )
    parser.add_argument(
        "--rebuilt",
        action="store_true",
        help="validate a rebuilt PDF against the declared rebuild-version allowlist",
    )
    parser.add_argument(
        "--require-tools",
        action="store_true",
        help="fail unless pdfinfo, pdftotext, and pdfdetach are all available",
    )
    args = parser.parse_args()

    path = Path(args.pdf)
    if path.is_symlink() or not path.is_file():
        print(f"ERROR: missing or irregular PDF: {path}", file=sys.stderr)
        return 1
    try:
        expected = _expectation(Path(args.project))
        if expected.get("file") != "Rooted_tree_Catalan_closure.pdf":
            raise PDFCheckError("project manuscript_pdf file identity drift")
        structural = inspect_pdf_bytes(path.read_bytes())
        if args.rebuilt:
            raw_versions = expected.get("rebuild_pdf_versions")
            if (
                not isinstance(raw_versions, list)
                or not raw_versions
                or not all(isinstance(item, str) for item in raw_versions)
            ):
                raise PDFCheckError("project manuscript_pdf rebuild-version allowlist is invalid")
            allowed_versions = set(raw_versions)
        else:
            allowed_versions = {str(expected.get("pdf_version"))}
        if structural["pdf_version"] not in allowed_versions:
            raise PDFCheckError(
                f"PDF header version drift: {structural['pdf_version']!r} not in "
                f"{sorted(allowed_versions)!r}"
            )

        required_tools = ("pdfinfo", "pdftotext", "pdfdetach")
        missing = [tool for tool in required_tools if shutil.which(tool) is None]
        if missing and args.require_tools:
            raise PDFCheckError("required PDF inspection tools are unavailable: " + ", ".join(missing))

        page_count: int | None = None
        if "pdfinfo" not in missing:
            fields = parse_pdfinfo(run_checked_tool(["pdfinfo", str(path)], "pdfinfo"))
            page_count = validate_pdfinfo(
                fields, expected, allowed_pdf_versions=allowed_versions
            )
        if "pdftotext" not in missing:
            text = run_checked_tool(["pdftotext", str(path), "-"], "pdftotext")
            if args.expected_text not in text:
                raise PDFCheckError(
                    f"expected manuscript text not found: {args.expected_text!r}"
                )
        if "pdfdetach" not in missing:
            detached = run_checked_tool(["pdfdetach", "-list", str(path)], "pdfdetach")
            match = re.fullmatch(r"\s*(\d+) embedded files?\s*", detached)
            if match is None or int(match.group(1)) != 0:
                raise PDFCheckError(f"PDF contains or ambiguously reports embedded files: {detached!r}")
    except (OSError, PDFCheckError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    detail = f", {page_count} pages" if page_count is not None else ""
    print(
        f"PDF check passed: {path} ({structural['size_bytes']} bytes{detail}, "
        f"PDF {structural['pdf_version']}, passive, single revision)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
