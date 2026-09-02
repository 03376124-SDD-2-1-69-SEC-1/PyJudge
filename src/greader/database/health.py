"""DB connectivity/schema check for Neon — used by the /health/db route."""

from __future__ import annotations

from sqlalchemy import text
from sqlmodel import Session

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
