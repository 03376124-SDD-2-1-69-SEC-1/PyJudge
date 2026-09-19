"""SQLKnowledgeDocumentRepository against real Postgres (CORE-09)."""

import pytest
from sqlalchemy.exc import IntegrityError

from greader.core.uploads.models import DocumentStatus, KnowledgeDocument
from greader.database.core.knowledge_document_repository import (
    SQLKnowledgeDocumentRepository,
)
from greader.database.session import SessionFactory

pytestmark = pytest.mark.postgres


def _document(
    filename: str = "lecture.pdf",
    object_key: str = "uploads/abc-lecture.pdf",
    content_hash: str = "a" * 64,
) -> KnowledgeDocument:
    return KnowledgeDocument(
        filename=filename,
        object_key=object_key,
        content_hash=content_hash,
    )


@pytest.mark.usefixtures("empty_core_tables")
def test_document_round_trips_through_postgres(
    session_factory: SessionFactory,
) -> None:
    repository = SQLKnowledgeDocumentRepository(session_factory)

    created = repository.create(_document())

    assert isinstance(created.id, int)
    assert repository.get(created.id) == created
    assert created.status is DocumentStatus.UPLOADED


@pytest.mark.usefixtures("empty_core_tables")
def test_lookup_by_content_hash_finds_the_existing_document(
    session_factory: SessionFactory,
) -> None:
    repository = SQLKnowledgeDocumentRepository(session_factory)
    created = repository.create(_document(content_hash="b" * 64))

    assert repository.get_by_content_hash("b" * 64) == created
    assert repository.get_by_content_hash("c" * 64) is None


@pytest.mark.usefixtures("empty_core_tables")
def test_duplicate_object_key_is_rejected(session_factory: SessionFactory) -> None:
    """`r2_object_key` is UNIQUE: one row per stored object, no silent overwrite."""
    repository = SQLKnowledgeDocumentRepository(session_factory)
    repository.create(_document(object_key="uploads/same-key.pdf"))

    with pytest.raises(IntegrityError):
        repository.create(
            _document(object_key="uploads/same-key.pdf", content_hash="d" * 64)
        )


@pytest.mark.usefixtures("empty_core_tables")
def test_get_on_unknown_id_returns_none(session_factory: SessionFactory) -> None:
    repository = SQLKnowledgeDocumentRepository(session_factory)

    assert repository.get(999_999) is None
