"""The in-memory NotificationRepository against the shared contract.

`tests/db/test_notification_repository.py` binds the same contract to the SQL
adapter, so a behaviour the two do not share fails there.
"""

import pytest

from questly.core.notifications.ports import NotificationRepository
from tests.contracts.notification_repository import NotificationRepositoryContract
from tests.fakes.notifications import FakeNotificationRepository


class TestFakeNotificationRepository(NotificationRepositoryContract):
    @pytest.fixture()
    def repository(self) -> NotificationRepository:
        return FakeNotificationRepository()
