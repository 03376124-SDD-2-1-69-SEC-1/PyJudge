"""Domain representation of an uploaded knowledge document."""

from dataclasses import dataclass

from questly.core.uploads.models import DocumentStatus, KnowledgeDocument, StoredObject

__all__ = [
    "DocumentLibraryItem",
    "DocumentStatus",
    "KnowledgeDocument",
    "StoredObject",
]


@dataclass(frozen=True, slots=True)
class DocumentLibraryItem:
    """A document in an Instructor's library with its saved-draft usage count."""

    document: KnowledgeDocument
    used_in: int
