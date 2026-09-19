"""Shared plumbing for adapter tests that talk to a real database.

Every fixture here hangs off `postgres_url` from `tests/conftest.py`, which
fails loudly rather than silently pointing at the shared team database.
"""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text

from greader.database.session import SessionFactory, build_session_factory

CORE_TABLES = ("core.assignments", "core.topics", "core.knowledge_documents")


@pytest.fixture(scope="module")
def session_factory(postgres_url: str) -> Generator[SessionFactory, None, None]:
    """Yield a session factory against the throwaway Neon branch."""
    engine = create_engine(postgres_url)
    try:
        yield build_session_factory(engine)
    finally:
        engine.dispose()


@pytest.fixture()
def empty_core_tables(session_factory: SessionFactory) -> Generator[None, None, None]:
    """Leave the core tables empty before and after each test.

    CASCADE reaches `core.test_cases` through its ON DELETE CASCADE parent, so a
    leftover child row cannot leak into the next test.
    """

    def truncate() -> None:
        with session_factory() as session:
            session.execute(text(f"TRUNCATE {', '.join(CORE_TABLES)} CASCADE"))
            session.commit()

    truncate()
    yield
    truncate()
