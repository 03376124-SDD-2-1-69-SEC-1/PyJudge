"""Lazy synchronous database infrastructure."""

import os
from collections.abc import Generator
from functools import lru_cache

from dotenv import load_dotenv
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import ArgumentError
from sqlmodel import Session, create_engine


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Configure the production engine only when a database session is needed."""
    load_dotenv()
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    try:
        url = make_url(database_url)
    except ArgumentError as exc:
        raise RuntimeError("DATABASE_URL must use postgresql+psycopg://") from exc
    if url.drivername != "postgresql+psycopg":
        raise RuntimeError("DATABASE_URL must use postgresql+psycopg://")
    return create_engine(url, echo=False)


def get_session() -> Generator[Session, None, None]:
    """Open a session on demand without eager engine creation."""
    with Session(get_engine()) as session:
        yield session


# This module — and everything under database/ — is the ONLY place allowed
# to import SQLModel/SQLAlchemy per database/README.md rule 5:
#   "อย่าให้ Core service import ORM หรือ storage client โดยตรง"
# core/* modules must only ever see a Protocol + a plain dataclass.
