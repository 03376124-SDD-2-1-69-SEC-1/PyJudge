"""SQLKnowledgeDocumentRepository against the shared contract, on real Postgres."""

import pytest
from sqlalchemy.exc import IntegrityError

from questly.core.uploads.models import KnowledgeDocument
from questly.database.core.knowledge_document_repository import (
    SQLKnowledgeDocumentRepository,
)
from questly.database.session import SessionFactory
from tests.contracts.knowledge_document_repository import (
    KnowledgeDocumentRepositoryContract,
)
from tests.db.rows import RealRows

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


class TestSQLKnowledgeDocumentRepository(RealRows, KnowledgeDocumentRepositoryContract):
    """Run the contract against the SQL adapter."""

    @pytest.fixture()
    def repository(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> SQLKnowledgeDocumentRepository:
        return SQLKnowledgeDocumentRepository(session_factory)


@pytest.mark.usefixtures("empty_core_tables")
def test_duplicate_object_key_is_rejected(session_factory: SessionFactory) -> None:
    """`r2_object_key` is UNIQUE: one row per stored object, no silent overwrite."""
    repository = SQLKnowledgeDocumentRepository(session_factory)
    repository.create(_document(object_key="uploads/same-key.pdf"))

    with pytest.raises(IntegrityError):
        repository.create(
            _document(object_key="uploads/same-key.pdf", content_hash="d" * 64)
        )
