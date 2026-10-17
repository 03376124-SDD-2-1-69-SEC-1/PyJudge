"""Temporary compatibility exports; remove this package with OPS-20."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from questly.core.documents.models import (
        DocumentLibraryItem,
        DocumentStatus,
        KnowledgeDocument,
        StoredObject,
    )


def __getattr__(name: str) -> object:
    if name == "DocumentLibraryItem":
        from questly.core.documents.models import DocumentLibraryItem

        return DocumentLibraryItem
    if name == "DocumentStatus":
        from questly.core.documents.models import DocumentStatus

        return DocumentStatus
    if name == "KnowledgeDocument":
        from questly.core.documents.models import KnowledgeDocument

        return KnowledgeDocument
    if name == "StoredObject":
        from questly.core.documents.models import StoredObject

        return StoredObject
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DocumentLibraryItem",
    "DocumentStatus",
    "KnowledgeDocument",
    "StoredObject",
]
