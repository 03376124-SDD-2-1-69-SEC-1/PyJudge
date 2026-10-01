"""Contract every DocumentCatalog implementation must satisfy.

The catalog is read-only, so each binding supplies `seed_document`, which
stores one Document however its store does. Bound to the in-memory adapter in
`tests/unit/core/generation/` and to `SQLDocumentCatalog` in `tests/db/`.
"""

from __future__ import annotations

from collections.abc import Callable

from questly.core.generation.models import DocumentSummary
from questly.core.generation.ports import DocumentCatalog
from tests.contracts.support import IdFactory, NeedsUsers

# (owner id, filename, pages or None, status) -> the stored Document's id
SeedDocument = Callable[[int, str, int | None, str], int]


class DocumentCatalogContract(NeedsUsers):
    """Checks that hold for any store behind DocumentCatalog."""

    def test_lists_an_owners_ready_documents_in_id_order(
        self,
        catalog: DocumentCatalog,
        seed_document: SeedDocument,
        new_user: IdFactory,
    ) -> None:
        mine, theirs = new_user(), new_user()
        first = seed_document(mine, "week1.pdf", 12, "ready")
        seed_document(theirs, "other.pdf", 3, "ready")
        second = seed_document(mine, "week2.pdf", 8, "ready")

        assert catalog.documents_of(mine) == [
            DocumentSummary(first, "week1.pdf", 12),
            DocumentSummary(second, "week2.pdf", 8),
        ]

    def test_leaves_out_documents_generation_cannot_read_yet(
        self,
        catalog: DocumentCatalog,
        seed_document: SeedDocument,
        new_user: IdFactory,
    ) -> None:
        owner = new_user()
        for status in ("uploaded", "ingesting", "failed"):
            seed_document(owner, f"{status}.pdf", 5, status)

        assert catalog.documents_of(owner) == []

    def test_unknown_page_count_reads_as_zero(
        self,
        catalog: DocumentCatalog,
        seed_document: SeedDocument,
        new_user: IdFactory,
    ) -> None:
        owner = new_user()
        doc = seed_document(owner, "scan.pdf", None, "ready")

        assert catalog.documents_of(owner) == [DocumentSummary(doc, "scan.pdf", 0)]
