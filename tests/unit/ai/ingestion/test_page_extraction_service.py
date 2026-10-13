"""Page-extraction service checks at the parser port seam."""

from dataclasses import dataclass, field

import pytest

from questly.ai.ingestion.models import (
    DocumentExtraction,
    ExtractedPage,
    PageExtractionOutcome,
)
from questly.ai.ingestion.ports import CorruptDocumentError
from questly.ai.ingestion.service import PageExtractionService


@dataclass(slots=True)
class RecordingExtractor:
    result: DocumentExtraction
    received: list[bytes] = field(default_factory=list)

    def extract(self, pdf_bytes: bytes) -> DocumentExtraction:
        self.received.append(pdf_bytes)
        return self.result


class FailingExtractor:
    def extract(self, pdf_bytes: bytes) -> DocumentExtraction:
        raise CorruptDocumentError(f"unreadable input of {len(pdf_bytes)} bytes")


def test_delegates_exact_bytes_and_returns_eager_result_unchanged() -> None:
    text = "น้ำ\n\tif ready:\n    print('กำลังทำ')\n"
    result = DocumentExtraction(
        (
            ExtractedPage(1, text, PageExtractionOutcome.EXTRACTED),
            ExtractedPage(2, "", PageExtractionOutcome.EMPTY),
            ExtractedPage(3, "partial", PageExtractionOutcome.NEEDS_OCR),
        )
    )
    extractor = RecordingExtractor(result)
    service = PageExtractionService(extractor)
    pdf_bytes = b"exact PDF bytes"

    extracted = service.extract(pdf_bytes)

    assert extractor.received == [pdf_bytes]
    assert extracted is result
    assert extracted.pages[0].text == text
    assert tuple(page.outcome for page in extracted.pages) == (
        PageExtractionOutcome.EXTRACTED,
        PageExtractionOutcome.EMPTY,
        PageExtractionOutcome.NEEDS_OCR,
    )


def test_preserves_typed_extractor_failures() -> None:
    service = PageExtractionService(FailingExtractor())

    with pytest.raises(CorruptDocumentError, match="4 bytes"):
        service.extract(b"fail")
