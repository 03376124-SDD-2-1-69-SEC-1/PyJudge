"""PyMuPDF adapter for eager, page-preserving PDF text extraction."""

import pymupdf

from greader.ai.ingestion.models import (
    DocumentExtraction,
    ExtractedPage,
    PageExtractionOutcome,
)
from greader.ai.ingestion.ports import CorruptDocumentError, EncryptedDocumentError

DOMINANT_IMAGE_COVERAGE = 0.8


def _normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _has_visible_nontext_content(page: pymupdf.Page) -> bool:
    """Return whether a textless page still contains visible page content."""
    return bool(page.get_image_info() or page.get_drawings())


def _has_dominant_image(page: pymupdf.Page) -> bool:
    """Detect scan-like images while allowing ordinary figures and logos."""
    page_area = page.rect.get_area()
    if page_area <= 0:
        return False
    return any(
        (pymupdf.Rect(image["bbox"]) & page.rect).get_area() / page_area
        >= DOMINANT_IMAGE_COVERAGE
        for image in page.get_image_info()
    )


class PyMuPDFPageExtractor:
    """Extract every physical PDF page without OCR or text rewriting."""

    def extract(self, pdf_bytes: bytes) -> DocumentExtraction:
        try:
            document = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
            raise CorruptDocumentError("input is not a readable PDF") from exc

        try:
            if document.needs_pass:
                raise EncryptedDocumentError("PDF requires a password")

            pages = tuple(
                self._extract_page(page, page_number)
                for page_number, page in enumerate(document, start=1)
            )
        except EncryptedDocumentError:
            raise
        except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
            raise CorruptDocumentError("a PDF page could not be decoded") from exc
        finally:
            document.close()

        return DocumentExtraction(pages)

    @staticmethod
    def _extract_page(page: pymupdf.Page, page_number: int) -> ExtractedPage:
        text = _normalize_line_endings(page.get_text())
        if text.strip() and not _has_dominant_image(page):
            outcome = PageExtractionOutcome.EXTRACTED
        elif _has_visible_nontext_content(page):
            outcome = PageExtractionOutcome.NEEDS_OCR
        else:
            outcome = PageExtractionOutcome.EMPTY
        return ExtractedPage(page_number, text, outcome)
