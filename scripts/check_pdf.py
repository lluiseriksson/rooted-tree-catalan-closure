#!/usr/bin/env python3
"""Perform structural and optional Poppler checks on a manuscript PDF."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf")
    parser.add_argument(
        "--expected-text",
        default="Rooted-tree summation and Catalan closure",
        help="text required when pdftotext is available",
    )
    args = parser.parse_args()
    path = Path(args.pdf)
    if not path.is_file():
        fail(f"missing PDF: {path}")
    data = path.read_bytes()
    if not data.startswith(b"%PDF-"):
        fail("file has no PDF header")
    if len(data) < 50_000:
        fail(f"PDF is unexpectedly small: {len(data)} bytes")
    if b"%%EOF" not in data[-4096:]:
        fail("PDF has no terminal EOF marker")
    page_count: int | None = None
    if shutil.which("pdfinfo"):
        proc = subprocess.run(["pdfinfo", str(path)], text=True, capture_output=True)
        if proc.returncode != 0:
            fail(f"pdfinfo failed:\n{proc.stdout}{proc.stderr}")
        match = re.search(r"(?m)^Pages:\s+(\d+)\s*$", proc.stdout)
        if not match:
            fail("pdfinfo did not report a page count")
        page_count = int(match.group(1))
        if page_count <= 0:
            fail("PDF page count is not positive")
    if shutil.which("pdftotext"):
        proc = subprocess.run(["pdftotext", str(path), "-"], text=True, capture_output=True)
        if proc.returncode != 0:
            fail(f"pdftotext failed:\n{proc.stdout}{proc.stderr}")
        if args.expected_text not in proc.stdout:
            fail(f"expected manuscript text not found: {args.expected_text!r}")
    detail = f", {page_count} pages" if page_count is not None else ""
    print(f"PDF check passed: {path} ({len(data)} bytes{detail})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
