"""PostgreSQL adapter for the vector repository port.

The adapter uses the existing RAG table definitions and receives a session
factory from the composition root. Importing this module does not read database
credentials or create an engine.
"""

from collections.abc import Callable, Mapping
from contextlib import AbstractContextManager
from typing import Any

from sqlalchemy import insert, literal, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import Session

from greader.ai.app.models import (
    ChunkSearchResult,
    Embedding,
    KnowledgeChunk,
    KnowledgeSource,
    NewKnowledgeChunk,
    NewKnowledgeSource,
    SourceCreationResult,
)
from greader.ai.app.repository import (
    DuplicateChunkError,
    DuplicateSourceError,
    VectorRepositoryError,
)
from greader.database.rag.tables import KnowledgeChunk as KnowledgeChunkTable
from greader.database.rag.tables import KnowledgeSource as KnowledgeSourceTable

SOURCE_UNIQUE_CONSTRAINT = "uq_knowledge_sources_core_document_id"
CHUNK_UNIQUE_CONSTRAINT = "uq_knowledge_chunks_source_content_hash"
SOURCE_TABLE = KnowledgeSourceTable.__table__
CHUNK_TABLE = KnowledgeChunkTable.__table__
SessionFactory = Callable[[], AbstractContextManager[Session]]


class PostgresVectorRepository:
    """Persist and search vectors through synchronous SQLAlchemy sessions."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def create_source_with_chunks(
        self,
        source: NewKnowledgeSource,
        chunks: tuple[NewKnowledgeChunk, ...],
    ) -> SourceCreationResult:
        """Insert one source and every chunk in one database transaction."""
        with self._session_factory() as session:
            try:
                source_row = session.execute(_source_insert(source)).mappings().one()
                source_id = source_row["id"]
                chunk_rows = tuple(
                    session.execute(_chunk_insert(source_id, chunk)).mappings().one()
                    for chunk in chunks
                )
                result = SourceCreationResult(
                    source=_source_from_row(source_row),
                    chunks=tuple(_chunk_from_row(row) for row in chunk_rows),
                )
                session.commit()
                return result
            except IntegrityError as exc:
                session.rollback()
                raise _translate_integrity_error(exc) from exc
            except SQLAlchemyError as exc:
                session.rollback()
                raise VectorRepositoryError("vector storage operation failed") from exc

    def search(
        self,
        embedding: Embedding,
        *,
        embedding_model: str,
        limit: int,
    ) -> list[ChunkSearchResult]:
        """Search non-null vectors for exactly one embedding model."""
        statement = _search_statement(
            embedding, embedding_model=embedding_model, limit=limit
        )
        with self._session_factory() as session:
            try:
                rows = session.execute(statement).mappings().all()
            except SQLAlchemyError as exc:
                session.rollback()
                raise VectorRepositoryError("vector search operation failed") from exc
        return [
            ChunkSearchResult(
                chunk_id=row["chunk_id"],
                source_id=row["source_id"],
                page=row["page"],
                text=row["text"],
                score=float(row["score"]),
            )
            for row in rows
        ]


def _source_insert(source: NewKnowledgeSource):
    return (
        insert(SOURCE_TABLE)
        .values(
            core_document_id=source.core_document_id,
            r2_object_key=source.r2_object_key,
            content_hash=source.content_hash,
            status=source.status,
            embedding_model=source.embedding_model,
            embedding_dim=source.embedding_dim,
            metadata=dict(source.metadata),
        )
        .returning(*SOURCE_TABLE.c)
    )


def _chunk_insert(source_id: int, chunk: NewKnowledgeChunk):
    return (
        insert(CHUNK_TABLE)
        .values(
            source_id=source_id,
            chunk_index=chunk.chunk_index,
            page=chunk.page,
            text=chunk.text,
            token_count=chunk.token_count,
            content_hash=chunk.content_hash,
            embedding_model=chunk.embedding_model,
            metadata=dict(chunk.metadata),
            embedding=list(chunk.embedding) if chunk.embedding is not None else None,
        )
        .returning(*CHUNK_TABLE.c)
    )


def _search_statement(embedding: Embedding, *, embedding_model: str, limit: int):
    cosine_distance = CHUNK_TABLE.c.embedding.cosine_distance(list(embedding))
    score = (literal(1.0) - cosine_distance).label("score")
    return (
        select(
            CHUNK_TABLE.c.id.label("chunk_id"),
            CHUNK_TABLE.c.source_id,
            CHUNK_TABLE.c.page,
            CHUNK_TABLE.c.text,
            score,
        )
        .where(
            CHUNK_TABLE.c.embedding.is_not(None),
            CHUNK_TABLE.c.embedding_model == embedding_model,
        )
        .order_by(score.desc(), CHUNK_TABLE.c.id.asc())
        .limit(limit)
    )


def _source_from_row(row: Mapping[str, Any]) -> KnowledgeSource:
    return KnowledgeSource(
        id=row["id"],
        core_document_id=row["core_document_id"],
        r2_object_key=row["r2_object_key"],
        content_hash=row["content_hash"],
        status=row["status"],
        embedding_model=row["embedding_model"],
        embedding_dim=row["embedding_dim"],
        metadata=dict(row["metadata"]),
    )


def _chunk_from_row(row: Mapping[str, Any]) -> KnowledgeChunk:
    stored_embedding = row["embedding"]
    return KnowledgeChunk(
        id=row["id"],
        source_id=row["source_id"],
        chunk_index=row["chunk_index"],
        page=row["page"],
        text=row["text"],
        token_count=row["token_count"],
        content_hash=row["content_hash"],
        embedding_model=row["embedding_model"],
        metadata=dict(row["metadata"]),
        embedding=(
            tuple(float(value) for value in stored_embedding)
            if stored_embedding is not None
            else None
        ),
    )


def _translate_integrity_error(error: IntegrityError) -> VectorRepositoryError:
    diagnostic = getattr(error.orig, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    if constraint_name == SOURCE_UNIQUE_CONSTRAINT:
        return DuplicateSourceError()
    if constraint_name == CHUNK_UNIQUE_CONSTRAINT:
        return DuplicateChunkError()
    return VectorRepositoryError("vector storage integrity constraint failed")
