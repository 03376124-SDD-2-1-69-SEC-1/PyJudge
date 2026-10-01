"""The in-memory DocumentCatalog against the shared contract.

The fake is a settable lookup, so its seeding fixture applies the catalog's
rules (ready only, unknown pages as 0) the way a store-backed catalog must.
`tests/db/test_document_catalog.py` binds the same contract to SQL.
"""

from itertools import count

import pytest

from questly.core.generation.models import DocumentSummary
from tests.contracts.document_catalog import DocumentCatalogContract, SeedDocument
from tests.fakes.generation import FakeDocumentCatalog


class TestFakeDocumentCatalog(DocumentCatalogContract):
    """Run the contract against the in-memory adapter."""

    @pytest.fixture()
    def catalog(self) -> FakeDocumentCatalog:
        return FakeDocumentCatalog()

    @pytest.fixture()
    def seed_document(self, catalog: FakeDocumentCatalog) -> SeedDocument:
        ids = count(1)

        def seed(owner: int, filename: str, pages: int | None, status: str) -> int:
            document_id = next(ids)
            if status != "ready":
                return document_id
            if pages is None:
                pages = 0
            catalog.by_owner.setdefault(owner, []).append(
                DocumentSummary(document_id, filename, pages)
            )
            return document_id

        return seed
