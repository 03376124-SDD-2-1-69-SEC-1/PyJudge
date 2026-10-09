"""Immutable results for every physical page of a PDF document."""

from dataclasses import dataclass
from enum import StrEnum


class PageExtractionOutcome(StrEnum):
    """Whether a page has usable text, is blank, or needs OCR."""

    EXTRACTED = "extracted"
    EMPTY = "empty"
    NEEDS_OCR = "needs_ocr"


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    """One physical PDF page, numbered from 1 in source order.

    ``text`` preserves the extracted characters and whitespace. EXTRACTED
    requires non-whitespace text. EMPTY is a genuinely blank page and may
    retain whitespace. NEEDS_OCR marks a page whose visible content cannot be
    represented adequately by its text layer; any partial text is retained.
    Absence of text alone does not distinguish a blank page from a scan.
    """

    page_number: int
    text: str
    outcome: PageExtractionOutcome

    def __post_init__(self) -> None:
        if self.page_number < 1:
            raise ValueError("page_number must start at 1")
        if not isinstance(self.outcome, PageExtractionOutcome):
            raise ValueError("outcome must be a PageExtractionOutcome")
        if self.outcome == PageExtractionOutcome.EXTRACTED and not self.text.strip():
            raise ValueError("extracted pages require non-whitespace text")
        if self.outcome == PageExtractionOutcome.EMPTY and self.text.strip():
            raise ValueError("empty pages cannot contain non-whitespace text")


@dataclass(frozen=True, slots=True)
class DocumentExtraction:
    """Eager results containing every physical page, including blank pages.

    Adapters must supply one entry per physical page, without filtering,
    deduplication, or reordering. The tuple length is the physical page count;
    numbering must be contiguous from 1. An empty tuple represents a readable
    document with zero physical pages, never a document-level failure.
    """

    pages: tuple[ExtractedPage, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.pages, tuple):
            raise TypeError("pages must be an immutable tuple")
        for expected_number, page in enumerate(self.pages, start=1):
            if page.page_number != expected_number:
                raise ValueError(
                    "pages must be in contiguous source order starting at 1"
                )
