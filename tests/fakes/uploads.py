"""Temporary compatibility re-exports; remove with OPS-20."""

from tests.fakes.documents import FakeKnowledgeDocumentRepository, FakeObjectStorage

__all__ = ["FakeKnowledgeDocumentRepository", "FakeObjectStorage"]
