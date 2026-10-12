"""SQLSystemHealthChecker probes the real database."""

import pytest

from questly.core.admin.models import ServiceHealthStatus
from questly.database.health import SQLSystemHealthChecker
from questly.database.session import SessionFactory

pytestmark = pytest.mark.postgres


def test_database_is_probed_and_reported_healthy(
    session_factory: SessionFactory,
) -> None:
    status = SQLSystemHealthChecker(
        session_factory,
        generation_available=False,
        sandbox_available=False,
        email_available=False,
    ).check_services_health()

    database = next(s for s in status.services if s.name == "database")
    assert database.status is ServiceHealthStatus.HEALTHY
    assert database.details is None
