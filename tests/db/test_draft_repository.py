"""SQLDraftRepository against the shared contract, on real Postgres."""

import pytest

from questly.database.core.draft_repository import SQLDraftRepository
from questly.database.session import SessionFactory
from tests.contracts.draft_repository import DraftRepositoryContract
from tests.db.rows import RealRows

pytestmark = pytest.mark.postgres


class TestSQLDraftRepository(RealRows, DraftRepositoryContract):
    """Run the contract against the SQL adapter."""

    @pytest.fixture()
    def repository(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> SQLDraftRepository:
        return SQLDraftRepository(session_factory)
