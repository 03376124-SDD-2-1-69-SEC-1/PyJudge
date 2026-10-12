"""PDF ingestion is atomic at the vector-storage port seam."""

from dataclasses import dataclass, field
from hashlib import sha256

import pytest

from questly.ai.app.models import (
    KnowledgeChunk,
    KnowledgeSource,
    NewKnowledgeChunk,
    NewKnowledgeSource,
    SourceCreationResult,
)
from questly.ai.ingestion.models import (
    DocumentExtraction,
    ExtractedPage,
    PageExtractionOutcome,
)
from questly.ai.ingestion.pipeline import IngestionError, PdfIngestionService


@dataclass(slots=True)
class FakeExtractor:
    pages: tuple[ExtractedPage, ...]

    def extract(self, pdf_bytes: bytes) -> DocumentExtraction:
        assert pdf_bytes == b"pdf bytes"
        return DocumentExtraction(self.pages)


@dataclass(slots=True)
class FakeEmbedder:
    texts: list[str] = field(default_factory=list)
    fail_on: int = 0

    @property
    def model(self) -> str:
        return "test-embedding-model"

    def embed(self, text: str) -> tuple[float, ...]:
        self.texts.append(text)
        if len(self.texts) == self.fail_on:
            raise RuntimeError("provider unavailable")
        return (1.0,) + (0.0,) * 767


@dataclass(slots=True)
class RecordingWriter:
    calls: list[tuple[NewKnowledgeSource, tuple[NewKnowledgeChunk, ...]]] = field(
        default_factory=list
    )

    def create_source_with_chunks(
        self, source: NewKnowledgeSource, chunks: tuple[NewKnowledgeChunk, ...]
    ) -> SourceCreationResult:
        self.calls.append((source, chunks))
        persisted_source = KnowledgeSource(
            id=11,
            core_document_id=source.core_document_id,
            r2_object_key=source.r2_object_key,
            content_hash=source.content_hash,
            status=source.status,
            embedding_model=source.embedding_model,
            embedding_dim=source.embedding_dim,
            metadata=source.metadata,
        )
        persisted_chunks = tuple(
            KnowledgeChunk(
                id=index + 1,
                source_id=11,
                chunk_index=chunk.chunk_index,
                page=chunk.page,
                text=chunk.text,
                token_count=chunk.token_count,
                content_hash=chunk.content_hash,
                embedding_model=chunk.embedding_model,
                metadata=chunk.metadata,
                embedding=chunk.embedding,
            )
            for index, chunk in enumerate(chunks)
        )
        return SourceCreationResult(persisted_source, persisted_chunks)


def test_ingests_complete_pdf_with_page_citations_and_vectors() -> None:
    extractor = FakeExtractor(
        (
            ExtractedPage(1, "โจทย์\n", PageExtractionOutcome.EXTRACTED),
            ExtractedPage(2, "", PageExtractionOutcome.EMPTY),
            ExtractedPage(3, "ข้อมูลนำเข้า\nN\n", PageExtractionOutcome.EXTRACTED),
        )
    )
    embedder = FakeEmbedder()
    writer = RecordingWriter()
    service = PdfIngestionService(extractor, embedder, writer)

    result = service.ingest(
        b"pdf bytes",
        core_document_id=7,
        r2_object_key="sources/example.pdf",
        metadata={"topic": "arrays"},
    )

    assert result.source.status == "ready"
    assert result.source.content_hash == sha256(b"pdf bytes").hexdigest()
    assert result.source.embedding_model == embedder.model
    assert result.source.embedding_dim == 768
    assert result.source.metadata == {"topic": "arrays"}
    assert [chunk.chunk_index for chunk in result.chunks] == [0, 1]
    assert [chunk.page for chunk in result.chunks] == [1, 3]
    assert [chunk.metadata for chunk in result.chunks] == [
        {"page_end": 1, "kind": "story"},
        {"page_end": 3, "kind": "io_examples"},
    ]
    assert [chunk.text for chunk in result.chunks] == embedder.texts
    assert all(len(chunk.embedding or ()) == 768 for chunk in result.chunks)
    assert len(writer.calls) == 1


def test_refuses_ocr_page_before_embedding_or_persistence() -> None:
    extractor = FakeExtractor(
        (ExtractedPage(1, "partial", PageExtractionOutcome.NEEDS_OCR),)
    )
    embedder = FakeEmbedder()
    writer = RecordingWriter()

    with pytest.raises(IngestionError, match="OCR"):
        PdfIngestionService(extractor, embedder, writer).ingest(
            b"pdf bytes", core_document_id=7, r2_object_key="source.pdf"
        )

    assert embedder.texts == []
    assert writer.calls == []


def test_provider_failure_does_not_write_partial_document() -> None:
    extractor = FakeExtractor(
        (ExtractedPage(1, "Story\nข้อมูลนำเข้า\nN", PageExtractionOutcome.EXTRACTED),)
    )
    embedder = FakeEmbedder(fail_on=2)
    writer = RecordingWriter()

    with pytest.raises(RuntimeError, match="provider unavailable"):
        PdfIngestionService(extractor, embedder, writer).ingest(
            b"pdf bytes", core_document_id=7, r2_object_key="source.pdf"
        )

    assert len(embedder.texts) == 2
    assert writer.calls == []


def test_blank_pdf_has_explicit_error() -> None:
    extractor = FakeExtractor((ExtractedPage(1, "", PageExtractionOutcome.EMPTY),))
    writer = RecordingWriter()

    with pytest.raises(IngestionError, match="no usable text"):
        PdfIngestionService(extractor, FakeEmbedder(), writer).ingest(
            b"pdf bytes", core_document_id=7, r2_object_key="source.pdf"
        )

    assert writer.calls == []
