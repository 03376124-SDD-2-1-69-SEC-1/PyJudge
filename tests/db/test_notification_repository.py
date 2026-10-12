"""SQLNotificationRepository against the shared contract, on real Postgres."""

import pytest

from questly.database.core.notification_repository import SQLNotificationRepository
from questly.database.session import SessionFactory
from tests.contracts.notification_repository import NotificationRepositoryContract
from tests.db.rows import RealRows

pytestmark = pytest.mark.postgres


class TestSQLNotificationRepository(RealRows, NotificationRepositoryContract):
    """Run the contract against the SQL adapter."""

    @pytest.fixture()
    def repository(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> SQLNotificationRepository:
        return SQLNotificationRepository(session_factory)
