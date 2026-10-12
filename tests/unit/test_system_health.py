"""SQLSystemHealthChecker without a database: what it claims and what it doesn't."""

from contextlib import AbstractContextManager

from sqlalchemy.exc import OperationalError
from sqlmodel import Session

from questly.core.admin.models import ServiceHealthStatus
from questly.database.health import CONFIGURED_NOT_PROBED, SQLSystemHealthChecker


def _unreachable_database() -> AbstractContextManager[Session]:
    raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_configured_adapters_say_they_were_not_probed() -> None:
    status = SQLSystemHealthChecker(
        _unreachable_database,
        generation_available=True,
        sandbox_available=True,
        email_available=False,
    ).check_services_health()

    by_name = {service.name: service for service in status.services}
    assert by_name["database"].status is ServiceHealthStatus.UNHEALTHY
    for name in ("AI generation", "code execution sandbox"):
        assert by_name[name].status is ServiceHealthStatus.HEALTHY
        assert by_name[name].details == CONFIGURED_NOT_PROBED
    assert by_name["email delivery"].status is ServiceHealthStatus.UNHEALTHY
    assert by_name["email delivery"].details == (
        "Email delivery adapter is not configured"
    )
