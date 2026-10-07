"""Shared plumbing for adapter tests that talk to a real database.

Every fixture here hangs off `postgres_url` from `tests/conftest.py`, which
fails loudly rather than silently pointing at the shared team database.
"""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text

from questly.database.session import SessionFactory, build_session_factory

# Every core table a test may write. `core.ai_settings` is left out on purpose:
# it holds the one seeded row the migration inserts.
CORE_TABLES = (
    "core.users",
    "core.email_verification_tokens",
    "core.sessions",
    "core.instructor_requests",
    "core.classrooms",
    "core.classroom_members",
    "core.assignments",
    "core.assignment_versions",
    "core.classroom_assignments",
    "core.submissions",
    "core.submission_test_results",
    "core.notifications",
    "core.drafts",
    "core.generation_events",
    "core.topics",
    "core.knowledge_documents",
    "core.generation_requests",
    "core.generation_artifacts",
)


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
