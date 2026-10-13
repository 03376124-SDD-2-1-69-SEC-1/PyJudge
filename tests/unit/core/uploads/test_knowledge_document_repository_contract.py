"""The in-memory KnowledgeDocumentRepository satisfies the shared contract."""

import pytest

from questly.core.uploads.ports import KnowledgeDocumentRepository
from tests.contracts.knowledge_document_repository import (
    KnowledgeDocumentRepositoryContract,
)
from tests.fakes.uploads import FakeKnowledgeDocumentRepository


class TestFakeKnowledgeDocumentRepository(KnowledgeDocumentRepositoryContract):
    """Run the contract against the fake."""

    @pytest.fixture()
    def repository(self) -> KnowledgeDocumentRepository:
        return FakeKnowledgeDocumentRepository()
