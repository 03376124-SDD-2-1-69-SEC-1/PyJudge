"""DB connectivity/schema check for Neon — used by the /health/db route."""

from __future__ import annotations

from importlib.util import find_spec

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from questly.core.admin.models import (
    ServiceHealthStatus,
    ServiceStatus,
    SystemStatus,
)
from questly.core.admin.ports import SystemHealthChecker
from questly.database.session import SessionFactory

EXPECTED_SCHEMAS = ("core", "rag")


def check_db(session: Session) -> dict:
    """Run a trivial query plus confirm expected schemas exist in Neon."""
    session.exec(text("SELECT 1"))

    rows = session.exec(
        text(
            "SELECT schema_name FROM information_schema.schemata "
            "WHERE schema_name = ANY(:schemas)"
        ).bindparams(schemas=list(EXPECTED_SCHEMAS))
    ).all()
    found = {row[0] for row in rows}

    return {
        "connected": True,
        "schemas": {name: name in found for name in EXPECTED_SCHEMAS},
    }


CONFIGURED_NOT_PROBED = "configured (not probed)"


class SQLSystemHealthChecker(SystemHealthChecker):
    """Probe the database; report whether the other adapters are configured.

    Only the database is actually contacted. PDF processing, AI generation,
    the sandbox and email say "configured (not probed)" when healthy, so A-01
    does not claim more than was checked.
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        generation_available: bool,
        sandbox_available: bool,
        email_available: bool,
    ) -> None:
        self._session_factory = session_factory
        self._generation_available = generation_available
        self._sandbox_available = sandbox_available
        self._email_available = email_available

    def check_services_health(self) -> SystemStatus:
        try:
            with self._session_factory() as session:
                database = check_db(session)
            database_ready = database["connected"] and all(database["schemas"].values())
        except SQLAlchemyError:
            database_ready = False

        return SystemStatus(
            services=[
                ServiceStatus("web application", ServiceHealthStatus.HEALTHY),
                self._probed(
                    "database",
                    database_ready,
                    "Database connection or required schemas unavailable",
                ),
                self._configured(
                    "PDF processing",
                    find_spec("fitz") is not None,
                    "PyMuPDF is not installed",
                ),
                self._configured(
                    "AI generation",
                    self._generation_available,
                    "Generation provider is not configured",
                ),
                self._configured(
                    "code execution sandbox",
                    self._sandbox_available,
                    "Code execution adapter is not configured",
                ),
                self._configured(
                    "email delivery",
                    self._email_available,
                    "Email delivery adapter is not configured",
                ),
            ]
        )

    @staticmethod
    def _probed(name: str, ready: bool, unavailable_detail: str) -> ServiceStatus:
        if ready:
            return ServiceStatus(name, ServiceHealthStatus.HEALTHY)
        return ServiceStatus(name, ServiceHealthStatus.UNHEALTHY, unavailable_detail)

    @staticmethod
    def _configured(name: str, configured: bool, missing_detail: str) -> ServiceStatus:
        if configured:
            return ServiceStatus(
                name, ServiceHealthStatus.HEALTHY, CONFIGURED_NOT_PROBED
            )
        return ServiceStatus(name, ServiceHealthStatus.UNHEALTHY, missing_detail)
