"""Synchronous PDF page-extraction port and document-level failures."""

from typing import Protocol

from greader.ai.ingestion.models import DocumentExtraction


class PageExtractionError(Exception):
    """Base error exposed by page-extraction adapters."""


class CorruptDocumentError(PageExtractionError):
    """The input is not a readable PDF or a page cannot be decoded.

    Adapters must fail the complete extraction rather than return partial
    results or silently skip an unreadable physical page.
    """


class EncryptedDocumentError(PageExtractionError):
    """The PDF requires a password; this port does not accept passwords."""


class PageExtractor(Protocol):
    """Extract pages without chunking, OCR, storage, or provider calls."""

    def extract(self, pdf_bytes: bytes) -> DocumentExtraction:
        """Return every physical page eagerly, numbered from 1 in source order.

        The caller supplies PDF bytes, so no file, stream, URL, or storage
        client crosses this boundary. The adapter owns and closes all parser
        documents and other resources it opens before returning or raising,
        including on page decoding failure. Results must remain usable after
        closing; do not return generators or parser-backed page objects.

        Normalize CRLF and bare CR line endings to LF only. Preserve Thai and
        English characters, combining marks, line boundaries, blank lines,
        spaces, tabs, and code indentation. Do not strip text, collapse
        whitespace, join lines, dehyphenate, apply Unicode normalization, or
        guess repairs for broken glyphs. Outcome classification may inspect
        whitespace without changing the returned text.

        Retain blank pages as EMPTY. Mark scans or unusable text layers as
        NEEDS_OCR, preserving any partial text; never run OCR here. A page
        with no extracted text is not necessarily blank: inspect page content
        before choosing EMPTY. EXTRACTED does not guarantee semantic accuracy.

        Translate parser failures into CorruptDocumentError and PDFs requiring
        passwords into EncryptedDocumentError. Do not return partial results
        for those failures or leak parser-specific exceptions.
        """
        ...
