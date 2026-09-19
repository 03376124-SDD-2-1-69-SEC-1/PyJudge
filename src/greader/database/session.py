"""Engine and session factory for the Neon database.

This module — and everything under `database/` — is the ONLY place allowed to
import SQLModel/SQLAlchemy per database/README.md rule 5:
  "อย่าให้ Core service import ORM หรือ storage client โดยตรง"
`core/*` modules must only ever see a Protocol + a plain dataclass.

Nothing here runs at import time. A repository adapter receives a session
factory through its constructor, and `main.py` is the only caller that builds
one, so importing this module never needs `DATABASE_URL` to be set.
"""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, create_engine

from greader.config import Settings, get_settings

SessionFactory = sessionmaker[Session]


def build_engine(settings: Settings) -> Engine:
    """Return an engine for the configured DSN.

    The `postgresql+psycopg://` driver tag is enforced in `greader.config`;
    a bare `postgresql://` URL resolves to psycopg2, which is not installed.
    """
    return create_engine(settings.database_url, echo=False)


def build_session_factory(engine: Engine) -> SessionFactory:
    """Return a factory that opens one session per unit of work.

    `expire_on_commit=False` so an adapter can read the row it just wrote —
    including the id the database assigned — after committing.
    """
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


@lru_cache(maxsize=1)
def _default_session_factory() -> SessionFactory:
    return build_session_factory(build_engine(get_settings()))


def get_session() -> Generator[Session, None, None]:
    """Yield a session for the `/health/db` route.

    Domain services never use this: they hold a repository built with a session
    factory. This exists because FastAPI's infrastructure health check is the
    one sanctioned `Depends()` in the application (see AGENTS.md).
    """
    with _default_session_factory()() as session:
        yield session
