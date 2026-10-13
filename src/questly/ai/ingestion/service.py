"""Page-extraction use case independent of a concrete PDF parser."""

from questly.ai.ingestion.models import DocumentExtraction
from questly.ai.ingestion.ports import PageExtractor


class PageExtractionService:
    """Expose eager page extraction through the module's parser port."""

    def __init__(self, extractor: PageExtractor) -> None:
        self._extractor = extractor

    def extract(self, pdf_bytes: bytes) -> DocumentExtraction:
        """Return the extractor result without rewriting page text or outcomes."""
        return self._extractor.extract(pdf_bytes)
