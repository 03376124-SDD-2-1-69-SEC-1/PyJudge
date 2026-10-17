"""The temporary uploads package continues to expose the document model."""

from questly.core.documents.models import KnowledgeDocument
from questly.core.uploads import KnowledgeDocument as LegacyPackageDocument
from questly.core.uploads.models import KnowledgeDocument as LegacyModuleDocument


def test_legacy_document_imports_resolve_to_the_same_model() -> None:
    assert LegacyPackageDocument is KnowledgeDocument
    assert LegacyModuleDocument is KnowledgeDocument
