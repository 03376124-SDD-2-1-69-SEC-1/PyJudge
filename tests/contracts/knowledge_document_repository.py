"""Contract every KnowledgeDocumentRepository implementation must satisfy.

Bound to the in-memory adapter in `tests/unit/core/uploads/` and to
`SQLKnowledgeDocumentRepository` in `tests/db/`.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from questly.core.uploads.models import DocumentStatus, KnowledgeDocument
from questly.core.uploads.ports import KnowledgeDocumentRepository
from tests.contracts.support import IdFactory, NeedsUsers


def _document(uploaded_by: int | None = None, suffix: str = "a") -> KnowledgeDocument:
    return KnowledgeDocument(
        filename=f"lecture-{suffix}.pdf",
        object_key=f"uploads/{suffix}-lecture.pdf",
        content_hash=suffix * 64,
        uploaded_by=uploaded_by,
    )


class KnowledgeDocumentRepositoryContract(NeedsUsers):
    """Checks that hold for any store behind KnowledgeDocumentRepository."""

    def test_create_assigns_an_id_and_keeps_the_uploader(
        self, repository: KnowledgeDocumentRepository, new_user: IdFactory
    ) -> None:
        uploader = new_user()

        created = repository.create(_document(uploaded_by=uploader))

        assert isinstance(created.id, int)
        assert created.uploaded_by == uploader
        assert created.status is DocumentStatus.UPLOADED
        assert created.page_count is None
        assert repository.get(created.id) == created

    def test_a_document_without_an_uploader_round_trips(
        self, repository: KnowledgeDocumentRepository
    ) -> None:
        created = repository.create(_document())

        assert repository.get(created.id) == created
        assert created.uploaded_by is None

    def test_get_on_an_unknown_id_returns_none(
        self, repository: KnowledgeDocumentRepository
    ) -> None:
        assert repository.get(999_999) is None

    def test_lookup_by_content_hash_finds_the_existing_document(
        self, repository: KnowledgeDocumentRepository
    ) -> None:
        created = repository.create(_document(suffix="b"))

        assert repository.get_by_content_hash("b" * 64) == created
        assert repository.get_by_content_hash("c" * 64) is None

    def test_update_stores_status_and_page_count_and_leaves_the_rest(
        self, repository: KnowledgeDocumentRepository, new_user: IdFactory
    ) -> None:
        created = repository.create(_document(uploaded_by=new_user()))

        ingesting = repository.update(replace(created, status=DocumentStatus.INGESTING))
        ready = repository.update(
            replace(ingesting, status=DocumentStatus.READY, page_count=12)
        )

        assert ingesting.status is DocumentStatus.INGESTING
        assert ready.status is DocumentStatus.READY
        assert ready.page_count == 12
        assert repository.get(created.id) == ready
        assert (ready.filename, ready.object_key, ready.content_hash) == (
            created.filename,
            created.object_key,
            created.content_hash,
        )
        assert ready.uploaded_by == created.uploaded_by

    def test_update_can_mark_a_document_failed(
        self, repository: KnowledgeDocumentRepository
    ) -> None:
        created = repository.create(_document())

        failed = repository.update(replace(created, status=DocumentStatus.FAILED))

        assert repository.get(created.id) == failed
        assert failed.status is DocumentStatus.FAILED

    def test_update_on_an_unknown_id_raises(
        self, repository: KnowledgeDocumentRepository
    ) -> None:
        with pytest.raises(KeyError):
            repository.update(replace(_document(), id=999_999))
