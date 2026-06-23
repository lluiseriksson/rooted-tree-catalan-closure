from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from check_pdf import PDFCheckError, inspect_pdf_bytes, parse_pdfinfo, validate_pdfinfo


class PDFCheckTests(unittest.TestCase):
    def minimal_pdf(self, body: bytes = b"1 0 obj\n<<>>\nendobj\n") -> bytes:
        return b"%PDF-1.5\n" + body + b"startxref\n0\n%%EOF\n"

    def test_structural_pdf_is_single_revision_and_passive(self) -> None:
        report = inspect_pdf_bytes(self.minimal_pdf(), minimum_size=0)
        self.assertEqual(report["pdf_version"], "1.5")
        self.assertEqual(report["eof_markers"], 1)
        self.assertEqual(report["startxref_markers"], 1)
        self.assertEqual(report["active_content_markers"], [])

    def test_structural_pdf_rejects_incremental_or_trailing_payloads(self) -> None:
        with self.assertRaisesRegex(PDFCheckError, "exactly one EOF"):
            inspect_pdf_bytes(self.minimal_pdf() + b"%%EOF\n", minimum_size=0)
        with self.assertRaisesRegex(PDFCheckError, "after its EOF"):
            inspect_pdf_bytes(self.minimal_pdf().rstrip(b"\n") + b"PAYLOAD", minimum_size=0)
        with self.assertRaisesRegex(PDFCheckError, "incremental updates"):
            inspect_pdf_bytes(
                b"%PDF-1.5\nstartxref\n0\nstartxref\n1\n%%EOF\n",
                minimum_size=0,
            )

    def test_structural_pdf_rejects_active_content_markers(self) -> None:
        for marker in (b"/JavaScript", b"/OpenAction", b"/EmbeddedFile", b"/Encrypt"):
            with self.subTest(marker=marker), self.assertRaisesRegex(
                PDFCheckError, "active-content"
            ):
                inspect_pdf_bytes(self.minimal_pdf(marker + b"\n"), minimum_size=0)

    def test_pdfinfo_contract_is_exact(self) -> None:
        fields = parse_pdfinfo(
            """Title: Example title
Author: Example author
Suspects: no
Form: none
JavaScript: no
Pages: 17
Encrypted: no
Page size: 595.28 x 841.89 pts (A4)
Page rot: 0
PDF version: 1.5
"""
        )
        pages = validate_pdfinfo(
            fields,
            {
                "title": "Example title",
                "author": "Example author",
                "pages": 17,
                "page_size": "A4",
                "pdf_version": "1.5",
                "encrypted": False,
                "javascript": False,
                "forms": False,
            },
        )
        self.assertEqual(pages, 17)
        fields["PDF version"] = "1.7"
        self.assertEqual(
            validate_pdfinfo(
                fields,
                {
                    "title": "Example title",
                    "author": "Example author",
                    "pages": 17,
                    "page_size": "A4",
                    "pdf_version": "1.5",
                    "encrypted": False,
                    "javascript": False,
                    "forms": False,
                },
                allowed_pdf_versions={"1.5", "1.7"},
            ),
            17,
        )
        with self.assertRaisesRegex(PDFCheckError, "PDF version drift"):
            validate_pdfinfo(
                fields,
                {
                    "title": "Example title",
                    "author": "Example author",
                    "pages": 17,
                    "page_size": "A4",
                    "pdf_version": "1.5",
                    "encrypted": False,
                    "javascript": False,
                    "forms": False,
                },
            )
        fields["PDF version"] = "1.5"
        fields["Pages"] = "18"
        with self.assertRaisesRegex(PDFCheckError, "page count drift"):
            validate_pdfinfo(
                fields,
                {
                    "title": "Example title",
                    "author": "Example author",
                    "pages": 17,
                    "page_size": "A4",
                    "pdf_version": "1.5",
                    "encrypted": False,
                    "javascript": False,
                    "forms": False,
                },
            )

    def test_pdfinfo_duplicate_fields_are_rejected(self) -> None:
        with self.assertRaisesRegex(PDFCheckError, "duplicate"):
            parse_pdfinfo("Pages: 17\nPages: 18\n")


if __name__ == "__main__":
    unittest.main()
