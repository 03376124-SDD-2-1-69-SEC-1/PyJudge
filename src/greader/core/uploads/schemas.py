"""Request and response schemas for the upload API."""

from pydantic import BaseModel

from greader.core.uploads.models import DocumentStatus


class KnowledgeDocumentResponse(BaseModel):
    """Public representation of an uploaded knowledge document.

    The bucket is deliberately absent: it is deployment configuration, and a
    client only ever needs the key to refer to the object.
    """

    id: int
    filename: str
    object_key: str
    content_hash: str
    status: DocumentStatus
