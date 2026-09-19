"""SQL adapter for the KnowledgeDocumentRepository port (CORE-09).

Translates between the `core.knowledge_documents` row and the plain dataclass in
`core/uploads/models.py`. This seam must live here, not on the `core/` side,
because it is the only layer allowed to see both.
"""

from __future__ import annotations

from sqlmodel import select

from greader.core.uploads.models import DocumentStatus, KnowledgeDocument
from greader.database.core.tables import KnowledgeDocument as KnowledgeDocumentRow
from greader.database.session import SessionFactory


def _to_domain(row: KnowledgeDocumentRow) -> KnowledgeDocument:
    return KnowledgeDocument(
        id=row.id,
        filename=row.filename,
        object_key=row.r2_object_key,
        content_hash=row.content_hash,
        status=DocumentStatus(row.status),
    )


class SQLKnowledgeDocumentRepository:
    """Store knowledge documents in the `core` schema.

    One session per method: the service is built once at startup, so there is no
    per-request session to join. Each call is its own unit of work.
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        """Initialize the adapter with a session factory."""
        self._session_factory = session_factory

    def create(self, document: KnowledgeDocument) -> KnowledgeDocument:
        """Insert a document and return it with the id the database assigned."""
        with self._session_factory() as session:
            row = KnowledgeDocumentRow(
                r2_object_key=document.object_key,
                filename=document.filename,
                content_hash=document.content_hash,
                status=document.status.value,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return _to_domain(row)

    def get(self, document_id: int) -> KnowledgeDocument | None:
        """Return a document by id when present."""
        with self._session_factory() as session:
            row = session.get(KnowledgeDocumentRow, document_id)
            if row is None:
                return None
            return _to_domain(row)

    def get_by_content_hash(self, content_hash: str) -> KnowledgeDocument | None:
        """Return the document already holding this content, when there is one."""
        with self._session_factory() as session:
            row = session.exec(
                select(KnowledgeDocumentRow).where(
                    KnowledgeDocumentRow.content_hash == content_hash
                )
            ).first()
            if row is None:
                return None
            return _to_domain(row)
