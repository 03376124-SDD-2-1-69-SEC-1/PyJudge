"""SQLAdminRepository against the shared contract, on real Postgres.

Usage this month is counted by SQLDraftRepository.count_all_generations,
whose contract runs in tests/db/test_draft_repository.py.
"""

from collections.abc import Generator

import pytest

from questly.core.admin.ports import AdminRepository
from questly.database.core.admin_repository import SQLAdminRepository
from questly.database.session import SessionFactory
from tests.contracts.admin_repository import AdminRepositoryContractTests

pytestmark = [pytest.mark.postgres, pytest.mark.usefixtures("empty_core_tables")]


class TestSQLAdminRepository(AdminRepositoryContractTests):
    """Run the contract against the SQL adapter."""

    @pytest.fixture()
    def repo(
        self, session_factory: SessionFactory
    ) -> Generator[AdminRepository, None, None]:
        repository = SQLAdminRepository(session_factory)
        original = repository.get_ai_settings()
        yield repository
        repository.update_ai_settings(original)
