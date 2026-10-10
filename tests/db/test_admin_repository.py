"""SQLAdminRepository against the shared contract, on real Postgres."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest

from questly.core.admin.domain import AISettingsUpdate
from questly.core.admin.ports import AdminRepository
from questly.core.auth.models import User
from questly.database.core.admin_repository import SQLAdminRepository
from questly.database.core.auth_repository import SQLAuthRepository
from questly.database.core.tables import GenerationEvent
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
        repository.update_ai_settings(
            AISettingsUpdate(
                model=original.model,
                daily_quota=original.daily_quota,
                max_pages=original.max_pages,
                require_citations=original.require_citations,
            )
        )

    def test_monthly_usage_counts_only_current_month(
        self, session_factory: SessionFactory
    ) -> None:
        now = datetime.now(UTC)
        previous_month = now.replace(day=1) - timedelta(days=1)
        owner = SQLAuthRepository(session_factory).create_user(
            User(
                email="usage@kmitl.ac.th",
                full_name="Usage",
                password_hash="scrypt$x",
            )
        )
        with session_factory() as session:
            session.add_all(
                [
                    GenerationEvent(user_id=owner.id, occurred_at=now),
                    GenerationEvent(user_id=owner.id, occurred_at=previous_month),
                ]
            )
            session.commit()

        assert SQLAdminRepository(session_factory).get_usage_this_month() == 1
