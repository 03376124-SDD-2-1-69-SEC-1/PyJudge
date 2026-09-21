"""SQLGenerationRepository against the shared contract, on real Postgres."""

import pytest

from greader.database.core.generation_repository import SQLGenerationRepository
from greader.database.session import SessionFactory
from tests.contracts.generation_repository import GenerationRepositoryContract

pytestmark = pytest.mark.postgres


class TestSQLGenerationRepository(GenerationRepositoryContract):
    """Run the contract against the SQL adapter."""

    @pytest.fixture()
    def repository(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> SQLGenerationRepository:
        return SQLGenerationRepository(session_factory)
