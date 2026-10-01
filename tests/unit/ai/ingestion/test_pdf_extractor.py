"""Concrete PyMuPDF adapter checks using PDFs built entirely in memory."""

from collections.abc import Iterator

import pymupdf
import pytest

from greader.ai.ingestion import pdf_extractor
from greader.ai.ingestion.models import PageExtractionOutcome
from greader.ai.ingestion.pdf_extractor import (
    PyMuPDFPageExtractor,
    _normalize_line_endings,
)
from greader.ai.ingestion.ports import CorruptDocumentError, EncryptedDocumentError


def _pdf_with_text_blank_and_vector_pages() -> bytes:
    document = pymupdf.open()
    text_page = document.new_page()
    text_page.insert_text((72, 72), "English\n    indented code")
    document.new_page()
    vector_page = document.new_page()
    vector_page.draw_rect(pymupdf.Rect(72, 72, 144, 144), fill=(0, 0, 0))
    pdf_bytes = document.tobytes()
    document.close()
    return pdf_bytes


def _encrypted_pdf() -> bytes:
    document = pymupdf.open()
    document.new_page().insert_text((72, 72), "secret")
    pdf_bytes = document.tobytes(
        encryption=pymupdf.PDF_ENCRYPT_AES_256,
        owner_pw="owner-password",
        user_pw="user-password",
    )
    document.close()
    return pdf_bytes


def test_extracts_every_page_in_source_order() -> None:
    result = PyMuPDFPageExtractor().extract(_pdf_with_text_blank_and_vector_pages())

    assert tuple(page.page_number for page in result.pages) == (1, 2, 3)
    assert result.pages[0].outcome == PageExtractionOutcome.EXTRACTED
    assert "English" in result.pages[0].text
    assert "    indented code" in result.pages[0].text
    assert result.pages[1].outcome == PageExtractionOutcome.EMPTY
    assert result.pages[2].outcome == PageExtractionOutcome.NEEDS_OCR


def test_rejects_corrupt_pdf_without_parser_error_leakage() -> None:
    with pytest.raises(CorruptDocumentError) as caught:
        PyMuPDFPageExtractor().extract(b"not a PDF")

    assert type(caught.value) is CorruptDocumentError


def test_rejects_password_protected_pdf() -> None:
    with pytest.raises(EncryptedDocumentError, match="password"):
        PyMuPDFPageExtractor().extract(_encrypted_pdf())


def test_normalizes_only_line_endings_and_preserves_thai_and_indentation() -> None:
    source = "น้ำ\r\n\tif ready:\r    print('กำลังทำ')"

    assert _normalize_line_endings(source) == ("น้ำ\n\tif ready:\n    print('กำลังทำ')")


def test_closes_document_when_page_decoding_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenPage:
        def get_text(self) -> str:
            raise RuntimeError("decode failed")

    class TrackedDocument:
        needs_pass = False

        def __init__(self) -> None:
            self.closed = False

        def __iter__(self) -> Iterator[BrokenPage]:
            return iter((BrokenPage(),))

        def close(self) -> None:
            self.closed = True

    document = TrackedDocument()

    def open_document(*, stream: bytes, filetype: str) -> TrackedDocument:
        assert stream == b"PDF bytes"
        assert filetype == "pdf"
        return document

    monkeypatch.setattr(pdf_extractor.pymupdf, "open", open_document)

    with pytest.raises(CorruptDocumentError, match="page"):
        PyMuPDFPageExtractor().extract(b"PDF bytes")

    assert document.closed
