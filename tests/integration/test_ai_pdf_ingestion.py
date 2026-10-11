"""One real PDF crosses extraction, chunking, embedding, and vector storage."""

import pymupdf

from questly.ai.app.service import VectorService
from questly.ai.ingestion.pdf_extractor import PyMuPDFPageExtractor
from questly.ai.ingestion.pipeline import PdfIngestionService
from tests.fakes.vector import FakeVectorRepository


class FixedEmbedder:
    @property
    def model(self) -> str:
        return "test-model"

    def embed(self, text: str) -> tuple[float, ...]:
        assert text.strip()
        return (1.0,) + (0.0,) * 767


def test_pdf_bytes_become_persisted_source_and_vector_chunk() -> None:
    pdf = pymupdf.open()
    try:
        pdf.new_page().insert_text((72, 72), "A sample programming problem")
        pdf.new_page().insert_text((72, 72), "Read N and print N")
        pdf_bytes = pdf.tobytes()
    finally:
        pdf.close()

    repository = FakeVectorRepository()
    service = PdfIngestionService(
        PyMuPDFPageExtractor(), FixedEmbedder(), VectorService(repository)
    )

    result = service.ingest(
        pdf_bytes,
        core_document_id=99,
        r2_object_key="sources/sample.pdf",
        metadata={"topic": "basics"},
    )

    assert result.source.id > 0
    assert result.source.status == "ready"
    assert len(result.chunks) == 1
    assert result.chunks[0].page == 1
    assert result.chunks[0].metadata["page_end"] == 2
    assert "A sample programming problem" in result.chunks[0].text
    assert "Read N and print N" in result.chunks[0].text
    assert len(result.chunks[0].embedding or ()) == 768
