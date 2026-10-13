"""Adapter that lets `core/uploads` ingest an uploaded PDF into the `rag` schema.

`core/uploads/ports.py` owns the DocumentIngestor port and `core/` never imports
`ai`, so this module is the seam: it wraps PdfIngestionService and translates
its failures into the port's one error. Only `main.py` builds it.
"""

from questly.ai.app.service import VectorValidationError
from questly.ai.embeddings.ports import EmbeddingError, EmbeddingProvider
from questly.ai.ingestion.models import DocumentExtraction
from questly.ai.ingestion.pipeline import (
    IngestionError,
    PdfIngestionService,
    VectorWriter,
)
from questly.ai.ingestion.ports import PageExtractionError, PageExtractor
from questly.core.uploads.models import IngestionOutcome, KnowledgeDocument
from questly.core.uploads.ports import DocumentIngestionError


class _CountingExtractor:
    """Hand the pipeline's extraction through and remember how many pages it had.

    PdfIngestionService does not report a page count, and extracting twice would
    parse the PDF twice. One instance serves one ingest call.
    """

    def __init__(self, extractor: PageExtractor) -> None:
        self._extractor = extractor
        self.page_count = 0

    def extract(self, pdf_bytes: bytes) -> DocumentExtraction:
        extraction = self._extractor.extract(pdf_bytes)
        self.page_count = len(extraction.pages)
        return extraction


class PdfDocumentIngestor:
    """Extract, chunk, embed and store one uploaded PDF."""

    def __init__(
        self,
        extractor: PageExtractor,
        embedder: EmbeddingProvider,
        writer: VectorWriter,
    ) -> None:
        self._extractor = extractor
        self._embedder = embedder
        self._writer = writer

    def ingest(self, document: KnowledgeDocument, data: bytes) -> IngestionOutcome:
        counter = _CountingExtractor(self._extractor)
        pipeline = PdfIngestionService(counter, self._embedder, self._writer)
        try:
            pipeline.ingest(
                data,
                core_document_id=document.id,
                r2_object_key=document.object_key,
            )
        except (
            IngestionError,
            PageExtractionError,
            EmbeddingError,
            VectorValidationError,
        ) as exc:
            raise DocumentIngestionError(str(exc)) from exc
        return IngestionOutcome(page_count=counter.page_count)


class UnavailableDocumentIngestor:
    """Fail every ingestion because no embedding provider is configured.

    The counterpart of StubGenerationClient for an app started without
    OPENROUTER_API_KEY: uploads still store, and the document ends up `failed`
    with the reason in the log instead of claiming to be searchable.
    """

    def ingest(self, document: KnowledgeDocument, data: bytes) -> IngestionOutcome:
        raise DocumentIngestionError("OPENROUTER_API_KEY is not set")
