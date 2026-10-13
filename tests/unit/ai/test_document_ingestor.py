"""The upload ingestor adapter maps the PDF pipeline onto core's port."""

from dataclasses import dataclass, field

import pytest

from questly.ai.app.models import (
    KnowledgeChunk,
    KnowledgeSource,
    NewKnowledgeChunk,
    NewKnowledgeSource,
    SourceCreationResult,
)
from questly.ai.embeddings.ports import EmbeddingError
from questly.ai.ingestion.models import (
    DocumentExtraction,
    ExtractedPage,
    PageExtractionOutcome,
)
from questly.ai.ingestion.ports import CorruptDocumentError
from questly.ai.ingestor import PdfDocumentIngestor, UnavailableDocumentIngestor
from questly.core.uploads.models import KnowledgeDocument
from questly.core.uploads.ports import DocumentIngestionError

DOCUMENT = KnowledgeDocument(
    id=7,
    filename="lecture.pdf",
    object_key="uploads/abc-lecture.pdf",
    content_hash="a" * 64,
)
EXTRACTED = DocumentExtraction(
    (
        ExtractedPage(1, "โจทย์\n", PageExtractionOutcome.EXTRACTED),
        ExtractedPage(2, "", PageExtractionOutcome.EMPTY),
        ExtractedPage(3, "ข้อมูลนำเข้า\nN\n", PageExtractionOutcome.EXTRACTED),
    )
)


@dataclass(slots=True)
class FakeExtractor:
    result: DocumentExtraction | None = None
    error: Exception | None = None
    seen: list[bytes] = field(default_factory=list)

    def extract(self, pdf_bytes: bytes) -> DocumentExtraction:
        self.seen.append(pdf_bytes)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


@dataclass(slots=True)
class FakeEmbedder:
    error: Exception | None = None

    @property
    def model(self) -> str:
        return "test-embedding-model"

    def embed(self, text: str) -> tuple[float, ...]:
        if self.error is not None:
            raise self.error
        return (1.0,) + (0.0,) * 767


@dataclass(slots=True)
class RecordingWriter:
    sources: list[NewKnowledgeSource] = field(default_factory=list)
    chunks: list[tuple[NewKnowledgeChunk, ...]] = field(default_factory=list)

    def create_source_with_chunks(
        self, source: NewKnowledgeSource, chunks: tuple[NewKnowledgeChunk, ...]
    ) -> SourceCreationResult:
        self.sources.append(source)
        self.chunks.append(chunks)
        return SourceCreationResult(
            KnowledgeSource(
                id=1,
                core_document_id=source.core_document_id,
                r2_object_key=source.r2_object_key,
                content_hash=source.content_hash,
                status=source.status,
                embedding_model=source.embedding_model,
                embedding_dim=source.embedding_dim,
                metadata=source.metadata,
            ),
            tuple(
                KnowledgeChunk(
                    id=index,
                    source_id=1,
                    chunk_index=chunk.chunk_index,
                    page=chunk.page,
                    text=chunk.text,
                    token_count=chunk.token_count,
                    content_hash=chunk.content_hash,
                    embedding_model=chunk.embedding_model,
                    metadata=chunk.metadata,
                    embedding=chunk.embedding,
                )
                for index, chunk in enumerate(chunks, start=1)
            ),
        )


def test_ingest_stores_the_pdf_under_the_core_document_and_reports_its_pages() -> None:
    extractor = FakeExtractor(EXTRACTED)
    writer = RecordingWriter()
    ingestor = PdfDocumentIngestor(extractor, FakeEmbedder(), writer)

    outcome = ingestor.ingest(DOCUMENT, b"pdf bytes")

    assert outcome.page_count == 3
    assert extractor.seen == [b"pdf bytes"]
    assert [source.core_document_id for source in writer.sources] == [7]
    assert [source.r2_object_key for source in writer.sources] == [
        "uploads/abc-lecture.pdf"
    ]
    assert len(writer.chunks[0]) == 2


def test_each_call_reports_its_own_page_count() -> None:
    one_page = DocumentExtraction(
        (ExtractedPage(1, "โจทย์\n", PageExtractionOutcome.EXTRACTED),)
    )
    extractor = FakeExtractor(EXTRACTED)
    ingestor = PdfDocumentIngestor(extractor, FakeEmbedder(), RecordingWriter())

    first = ingestor.ingest(DOCUMENT, b"pdf bytes")
    extractor.result = one_page
    second = ingestor.ingest(DOCUMENT, b"pdf bytes")

    assert (first.page_count, second.page_count) == (3, 1)


@pytest.mark.parametrize(
    "extractor",
    [
        FakeExtractor(error=CorruptDocumentError("input is not a readable PDF")),
        FakeExtractor(
            DocumentExtraction(
                (ExtractedPage(1, "scan", PageExtractionOutcome.NEEDS_OCR),)
            )
        ),
        FakeExtractor(
            DocumentExtraction((ExtractedPage(1, " \n", PageExtractionOutcome.EMPTY),))
        ),
    ],
    ids=["corrupt", "needs-ocr", "no-text"],
)
def test_unreadable_pdfs_become_a_document_ingestion_error(
    extractor: FakeExtractor,
) -> None:
    writer = RecordingWriter()
    ingestor = PdfDocumentIngestor(extractor, FakeEmbedder(), writer)

    with pytest.raises(DocumentIngestionError):
        ingestor.ingest(DOCUMENT, b"pdf bytes")

    assert writer.sources == []


def test_an_embedding_failure_stores_nothing() -> None:
    writer = RecordingWriter()
    ingestor = PdfDocumentIngestor(
        FakeExtractor(EXTRACTED),
        FakeEmbedder(error=EmbeddingError("OpenRouter embedding call failed")),
        writer,
    )

    with pytest.raises(DocumentIngestionError, match="OpenRouter embedding"):
        ingestor.ingest(DOCUMENT, b"pdf bytes")

    assert writer.sources == []


def test_the_unavailable_ingestor_fails_every_document() -> None:
    with pytest.raises(DocumentIngestionError, match="OPENROUTER_API_KEY"):
        UnavailableDocumentIngestor().ingest(DOCUMENT, b"pdf bytes")
