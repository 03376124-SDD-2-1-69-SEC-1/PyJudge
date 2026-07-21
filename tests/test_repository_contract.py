"""Repository contract tests.

These tests verify that both InMemoryAssignmentRepository and
SqlAlchemyAssignmentRepository satisfy the AssignmentRepository protocol.
"""

import pytest
from sqlalchemy.orm import sessionmaker

from greader.assignments.models import (
    Assignment,
    Difficulty,
    ReviewStatus,
    TestCase,
    TestCaseCategory,
)
from greader.assignments.repository import InMemoryAssignmentRepository
from greader.assignments.sql_repository import SqlAlchemyAssignmentRepository
from greader.db_models import Base

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_assignment(
    assignment_id: str = "a-1",
    title: str = "Test Assignment",
    *,
    test_cases: list[TestCase] | None = None,
) -> Assignment:
    """Build a minimal Assignment for testing."""
    return Assignment(
        id=assignment_id,
        title=title,
        description="A description",
        constraints="None",
        difficulty=Difficulty.EASY,
        programming_language="Python",
        status="Draft",
        reference_solution="pass",
        test_cases=test_cases or [],
    )


def _make_test_case(
    tc_id: str = "tc-1",
    category: TestCaseCategory = TestCaseCategory.NORMAL,
    status: ReviewStatus = ReviewStatus.PENDING,
) -> TestCase:
    """Build a minimal TestCase for testing."""
    return TestCase(
        id=tc_id,
        input_data="1 2\n3",
        expected_output="0 1",
        category=category,
        status=status,
        explanation="Test explanation",
    )


# ---------------------------------------------------------------------------
# Fixtures — one per implementation
# ---------------------------------------------------------------------------


@pytest.fixture()
def in_memory_repo() -> InMemoryAssignmentRepository:
    return InMemoryAssignmentRepository()


@pytest.fixture()
def sql_repo() -> SqlAlchemyAssignmentRepository:
    from greader.database import build_engine

    engine = build_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    return SqlAlchemyAssignmentRepository(factory)


@pytest.fixture(params=["in_memory", "sqlalchemy"])
def repo(request, in_memory_repo, sql_repo):
    """Parametrised fixture that yields both repository implementations."""
    if request.param == "in_memory":
        return in_memory_repo
    return sql_repo


# ---------------------------------------------------------------------------
# Contract tests — run once per implementation
# ---------------------------------------------------------------------------


class TestRepositoryContract:
    """Tests that apply equally to every AssignmentRepository implementation."""

    def test_get_nonexistent_returns_none(self, repo):
        assert repo.get_assignment("does-not-exist") is None

    def test_save_and_retrieve(self, repo):
        assignment = _make_assignment()
        repo.save_assignment(assignment)
        result = repo.get_assignment("a-1")
        assert result is not None
        assert result.id == "a-1"
        assert result.title == "Test Assignment"

    def test_list_multiple(self, repo):
        repo.save_assignment(_make_assignment("a-1", "First"))
        repo.save_assignment(_make_assignment("a-2", "Second"))
        assignments = repo.list_assignments()
        assert len(assignments) == 2
        titles = {a.title for a in assignments}
        assert titles == {"First", "Second"}

    def test_update_existing(self, repo):
        repo.save_assignment(_make_assignment("a-1", "Original"))
        repo.save_assignment(_make_assignment("a-1", "Updated"))
        result = repo.get_assignment("a-1")
        assert result is not None
        assert result.title == "Updated"
        assert len(repo.list_assignments()) == 1

    def test_persist_test_cases(self, repo):
        tc1 = _make_test_case("tc-1", TestCaseCategory.NORMAL, ReviewStatus.APPROVED)
        tc2 = _make_test_case("tc-2", TestCaseCategory.BOUNDARY, ReviewStatus.PENDING)
        assignment = _make_assignment("a-1", test_cases=[tc1, tc2])
        repo.save_assignment(assignment)
        result = repo.get_assignment("a-1")
        assert result is not None
        assert len(result.test_cases) == 2

    def test_preserve_enum_values(self, repo):
        tc = _make_test_case(
            category=TestCaseCategory.CORNER,
            status=ReviewStatus.REJECTED,
        )
        assignment = _make_assignment(test_cases=[tc])
        assignment.difficulty = Difficulty.HARD
        repo.save_assignment(assignment)
        result = repo.get_assignment("a-1")
        assert result is not None
        assert result.difficulty == Difficulty.HARD
        assert result.test_cases[0].category == TestCaseCategory.CORNER
        assert result.test_cases[0].status == ReviewStatus.REJECTED

    def test_delete_existing(self, repo):
        repo.save_assignment(_make_assignment("a-1"))
        assert repo.delete_assignment("a-1") is True
        assert repo.get_assignment("a-1") is None

    def test_delete_nonexistent(self, repo):
        assert repo.delete_assignment("does-not-exist") is False

    def test_cascade_delete_test_cases(self, repo):
        tc = _make_test_case()
        assignment = _make_assignment(test_cases=[tc])
        repo.save_assignment(assignment)
        repo.delete_assignment("a-1")
        # After deletion the assignment is gone.
        assert repo.get_assignment("a-1") is None


# ---------------------------------------------------------------------------
# SQLAlchemy-specific tests
# ---------------------------------------------------------------------------


class TestSqlAlchemySpecific:
    """Tests that only apply to the SQLAlchemy implementation."""

    def test_data_survives_new_session(self):
        """Data persists across independent sessions (not just in-process cache)."""
        from greader.database import build_engine

        engine = build_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        factory1 = sessionmaker(bind=engine)
        repo1 = SqlAlchemyAssignmentRepository(factory1)
        repo1.save_assignment(_make_assignment("a-1", "Persisted"))

        # Create a second sessionmaker (same engine) to simulate a new session.
        factory2 = sessionmaker(bind=engine)
        repo2 = SqlAlchemyAssignmentRepository(factory2)
        result = repo2.get_assignment("a-1")
        assert result is not None
        assert result.title == "Persisted"

    def test_enum_stored_as_string_value(self):
        """Enum values must be stored as 'Easy', not 'Difficulty.EASY'."""
        from greader.database import build_engine

        engine = build_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        factory = sessionmaker(bind=engine)
        repo = SqlAlchemyAssignmentRepository(factory)

        tc = _make_test_case(
            category=TestCaseCategory.BOUNDARY,
            status=ReviewStatus.APPROVED,
        )
        assignment = _make_assignment(test_cases=[tc])
        assignment.difficulty = Difficulty.MEDIUM
        repo.save_assignment(assignment)

        # Query the raw DB to verify string storage.
        with factory() as session:
            from greader.db_models import AssignmentRecord, TestCaseRecord

            record = session.get(AssignmentRecord, "a-1")
            assert record is not None
            assert record.difficulty == "Medium"

            tc_record = (
                session.query(TestCaseRecord).filter_by(assignment_id="a-1").first()
            )
            assert tc_record is not None
            assert tc_record.category == "Boundary"
            assert tc_record.status == "Approved"

    def test_cascade_delete_in_db(self):
        """Verify test case rows are actually removed from the DB on delete."""
        from greader.database import build_engine

        engine = build_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        factory = sessionmaker(bind=engine)
        repo = SqlAlchemyAssignmentRepository(factory)

        tc = _make_test_case()
        repo.save_assignment(_make_assignment(test_cases=[tc]))
        repo.delete_assignment("a-1")

        with factory() as session:
            from greader.db_models import TestCaseRecord

            remaining = session.query(TestCaseRecord).count()
            assert remaining == 0


# ---------------------------------------------------------------------------
# Environment tests
# ---------------------------------------------------------------------------


class TestEnvironmentConfig:
    """Verify the test database configuration."""

    def test_app_env_is_test(self):
        import os

        assert os.environ.get("APP_ENV") == "test"

    def test_database_url_is_test(self):
        import os

        url = os.environ.get("DATABASE_URL", "")
        assert ":memory:" in url or "test" in url.lower()
