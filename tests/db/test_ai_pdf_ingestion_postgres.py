"""AI-04 stores an extracted PDF and its vector in throwaway PostgreSQL."""

from secrets import randbelow

import pymupdf
import pytest
from sqlalchemy import delete, select

from questly.ai.app.service import VectorService
from questly.ai.ingestion.pdf_extractor import PyMuPDFPageExtractor
from questly.ai.ingestion.pipeline import PdfIngestionService
from questly.database.rag.tables import KnowledgeChunk, KnowledgeSource
from questly.database.rag.vector_repository import PostgresVectorRepository
from questly.database.session import SessionFactory

pytestmark = pytest.mark.postgres


class FixedEmbedder:
    @property
    def model(self) -> str:
        return "test-embedding-model"

    def embed(self, text: str) -> tuple[float, ...]:
        assert text.strip()
        return (1.0,) + (0.0,) * 767


def test_one_pdf_reaches_rag_source_and_vector_chunk(
    session_factory: SessionFactory,
) -> None:
    pdf = pymupdf.open()
    try:
        pdf.new_page().insert_text((72, 72), "One programming problem")
        pdf_bytes = pdf.tobytes()
    finally:
        pdf.close()

    core_document_id = randbelow(2**60) + 1
    service = PdfIngestionService(
        PyMuPDFPageExtractor(),
        FixedEmbedder(),
        VectorService(PostgresVectorRepository(session_factory)),
    )
    result = service.ingest(
        pdf_bytes,
        core_document_id=core_document_id,
        r2_object_key=f"tests/ai-04/{core_document_id}.pdf",
        metadata={"topic": "basics"},
    )

    source_table = KnowledgeSource.__table__
    chunk_table = KnowledgeChunk.__table__
    try:
        with session_factory() as session:
            source = (
                session.execute(
                    select(source_table).where(source_table.c.id == result.source.id)
                )
                .mappings()
                .one()
            )
            chunk = (
                session.execute(
                    select(chunk_table).where(
                        chunk_table.c.source_id == result.source.id
                    )
                )
                .mappings()
                .one()
            )
        assert source["status"] == "ready"
        assert source["core_document_id"] == core_document_id
        assert source["embedding_dim"] == 768
        assert source["metadata"] == {"topic": "basics"}
        assert chunk["page"] == 1
        assert chunk["embedding_model"] == "test-embedding-model"
        assert len(chunk["embedding"]) == 768
    finally:
        with session_factory() as session:
            session.execute(
                delete(source_table).where(source_table.c.id == result.source.id)
            )
            session.commit()
