"""SQLDocumentCatalog against the shared contract, on real Postgres."""

from itertools import count

import pytest

from questly.database.core.document_catalog_repository import SQLDocumentCatalog
from questly.database.core.tables import KnowledgeDocument as DocumentRow
from questly.database.session import SessionFactory
from tests.contracts.document_catalog import DocumentCatalogContract, SeedDocument
from tests.db.rows import RealRows

pytestmark = pytest.mark.postgres


class TestSQLDocumentCatalog(RealRows, DocumentCatalogContract):
    """Run the contract against the SQL adapter."""

    @pytest.fixture()
    def catalog(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> SQLDocumentCatalog:
        return SQLDocumentCatalog(session_factory)

    @pytest.fixture()
    def seed_document(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> SeedDocument:
        keys = count(1)

        def seed(owner: int, filename: str, pages: int | None, status: str) -> int:
            key = next(keys)
            with session_factory() as session:
                row = DocumentRow(
                    r2_object_key=f"documents/{key}.pdf",
                    filename=filename,
                    content_hash=f"hash-{key}",
                    status=status,
                    uploaded_by=owner,
                    page_count=pages,
                )
                session.add(row)
                session.commit()
                return row.id

        return seed
