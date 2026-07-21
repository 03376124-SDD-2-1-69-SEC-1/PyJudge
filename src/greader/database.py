"""Database engine and session factory."""

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


@event.listens_for(Engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:
    """Enable foreign key constraints for SQLite connections."""
    if type(dbapi_connection).__module__ == "sqlite3":
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def build_engine(database_url: str):
    """Create a SQLAlchemy engine for the given URL.

    For SQLite databases ``check_same_thread`` is disabled so that the
    same connection can be used across threads (as required by FastAPI's
    default thread-pool executor).
    """
    connect_args: dict = {}
    if database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    return create_engine(database_url, connect_args=connect_args)


def build_session_factory(database_url: str) -> sessionmaker[Session]:
    """Return a :class:`sessionmaker` bound to an engine for *database_url*."""
    engine = build_engine(database_url)
    return sessionmaker(bind=engine)
