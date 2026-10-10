"""DB connectivity/schema check for Neon — used by the /health/db route."""

from __future__ import annotations

from importlib.util import find_spec

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session

from questly.core.admin.domain import (
    ServiceHealthStatus,
    ServiceStatus,
    SystemStatusResponse,
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


class SQLSystemHealthChecker(SystemHealthChecker):
    """Check database connectivity and report configured runtime adapters."""

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

    def check_services_health(self) -> SystemStatusResponse:
        try:
            with self._session_factory() as session:
                database = check_db(session)
            database_ready = database["connected"] and all(database["schemas"].values())
        except SQLAlchemyError:
            database_ready = False

        return SystemStatusResponse(
            services=[
                self._status("web application", True),
                self._status(
                    "database",
                    database_ready,
                    "Database connection or required schemas unavailable",
                ),
                self._status(
                    "PDF processing",
                    find_spec("fitz") is not None,
                    "PyMuPDF is not installed",
                ),
                self._status(
                    "AI generation",
                    self._generation_available,
                    "Generation provider is not configured",
                ),
                self._status(
                    "code execution sandbox",
                    self._sandbox_available,
                    "Code execution adapter is not configured",
                ),
                self._status(
                    "email delivery",
                    self._email_available,
                    "Email delivery adapter is not configured",
                ),
            ]
        )

    @staticmethod
    def _status(
        name: str, ready: bool, unavailable_detail: str | None = None
    ) -> ServiceStatus:
        return ServiceStatus(
            name=name,
            status=(
                ServiceHealthStatus.HEALTHY if ready else ServiceHealthStatus.UNHEALTHY
            ),
            details=None if ready else unavailable_detail,
        )
