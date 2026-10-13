"""Fake-based checks for the page-extraction domain boundary, without PDFs."""

from dataclasses import FrozenInstanceError, dataclass

import pytest

from questly.ai.ingestion.models import (
    DocumentExtraction,
    ExtractedPage,
    PageExtractionOutcome,
)
from questly.ai.ingestion.ports import (
    CorruptDocumentError,
    EncryptedDocumentError,
    PageExtractionError,
    PageExtractor,
)


@dataclass(frozen=True, slots=True)
class FakePageExtractor:
    """Return configured page results through the same port as a future adapter."""

    result: DocumentExtraction

    def extract(self, pdf_bytes: bytes) -> DocumentExtraction:
        if pdf_bytes == b"corrupt":
            raise CorruptDocumentError("unreadable PDF")
        if pdf_bytes == b"encrypted":
            raise EncryptedDocumentError("password required")
        return self.result


def test_port_preserves_all_pages_and_exact_multilingual_text() -> None:
    text = "ข้อมูลนำเข้า English\n\nif ready:\n    print('กำลังทำ')\n\treturn 1\n"
    pages = (
        ExtractedPage(1, text, PageExtractionOutcome.EXTRACTED),
        ExtractedPage(2, "", PageExtractionOutcome.EMPTY),
        ExtractedPage(3, "", PageExtractionOutcome.NEEDS_OCR),
        ExtractedPage(4, text, PageExtractionOutcome.EXTRACTED),
        ExtractedPage(5, "partial ไทย", PageExtractionOutcome.NEEDS_OCR),
        ExtractedPage(6, " \n\t", PageExtractionOutcome.EMPTY),
    )
    extractor: PageExtractor = FakePageExtractor(DocumentExtraction(pages))

    result = extractor.extract(b"fake PDF")

    assert result.pages == pages
    assert len(result.pages) == 6
    assert tuple(page.page_number for page in result.pages) == (1, 2, 3, 4, 5, 6)
    assert result.pages[0].text == text
    assert result.pages[1].text == ""
    assert result.pages[2].outcome == PageExtractionOutcome.NEEDS_OCR
    assert result.pages[3].text == text
    assert result.pages[4].text == "partial ไทย"
    assert result.pages[5].text == " \n\t"


def test_thai_combining_characters_are_preserved_exactly() -> None:
    text = "\u0e19\u0e49\u0e33\n    English\n\t\u0e01\u0e34\u0e48"
    page = ExtractedPage(1, text, PageExtractionOutcome.EXTRACTED)
    extractor: PageExtractor = FakePageExtractor(DocumentExtraction((page,)))

    result = extractor.extract(b"fake PDF")

    assert result.pages[0].text.encode("utf-8") == text.encode("utf-8")


def test_zero_page_document_is_distinct_from_failure() -> None:
    extractor: PageExtractor = FakePageExtractor(DocumentExtraction(()))

    assert extractor.extract(b"zero pages").pages == ()


@pytest.mark.parametrize("page_number", [0, -1])
def test_page_numbers_are_one_based(page_number: int) -> None:
    with pytest.raises(ValueError, match="start at 1"):
        ExtractedPage(page_number, "text", PageExtractionOutcome.EXTRACTED)


@pytest.mark.parametrize("numbers", [(2,), (1, 3), (2, 1), (1, 1)])
def test_result_rejects_missing_reordered_and_duplicate_page_numbers(
    numbers: tuple[int, ...],
) -> None:
    pages = tuple(
        ExtractedPage(number, "text", PageExtractionOutcome.EXTRACTED)
        for number in numbers
    )

    with pytest.raises(ValueError, match="contiguous source order"):
        DocumentExtraction(pages)


@pytest.mark.parametrize("text", ["", " \n\t"])
def test_extracted_outcome_requires_text(text: str) -> None:
    with pytest.raises(ValueError, match="require non-whitespace text"):
        ExtractedPage(1, text, PageExtractionOutcome.EXTRACTED)


def test_empty_outcome_rejects_non_whitespace_text() -> None:
    with pytest.raises(ValueError, match="cannot contain non-whitespace text"):
        ExtractedPage(1, "ไทย", PageExtractionOutcome.EMPTY)


def test_unknown_outcome_is_rejected() -> None:
    with pytest.raises(ValueError, match="PageExtractionOutcome"):
        ExtractedPage(1, "", "unknown")  # type: ignore[arg-type]


def test_results_are_frozen_and_slotted() -> None:
    page = ExtractedPage(1, "text", PageExtractionOutcome.EXTRACTED)
    result = DocumentExtraction((page,))

    with pytest.raises(FrozenInstanceError):
        page.text = "changed"  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.pages = ()  # type: ignore[misc]
    assert not hasattr(page, "__dict__")
    assert not hasattr(result, "__dict__")


def test_result_rejects_mutable_page_collection() -> None:
    with pytest.raises(TypeError, match="immutable tuple"):
        DocumentExtraction([])  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("pdf_bytes", "error_type"),
    [(b"corrupt", CorruptDocumentError), (b"encrypted", EncryptedDocumentError)],
)
def test_port_exposes_typed_document_failures(
    pdf_bytes: bytes, error_type: type[PageExtractionError]
) -> None:
    extractor: PageExtractor = FakePageExtractor(DocumentExtraction(()))

    with pytest.raises(error_type):
        extractor.extract(pdf_bytes)
