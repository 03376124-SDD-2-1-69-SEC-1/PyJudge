"""SQLAuthRepository against the shared contract, on real Postgres."""

import pytest

from questly.database.core.auth_repository import SQLAuthRepository
from questly.database.session import SessionFactory
from tests.contracts.auth_repository import AuthRepositoryContract

pytestmark = pytest.mark.postgres


class TestSQLAuthRepository(AuthRepositoryContract):
    """Run the contract against the SQL adapter."""

    @pytest.fixture()
    def repository(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> SQLAuthRepository:
        return SQLAuthRepository(session_factory)
