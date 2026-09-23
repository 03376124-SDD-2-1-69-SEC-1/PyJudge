"""SQLAssignmentRepository against the shared contract, on real Postgres.

The same checks the in-memory adapter passes in
`tests/unit/core/assignments/test_repository_contract.py` (CORE-10), plus the
database facts a fake cannot prove.
"""

import pytest
from sqlalchemy import text

from greader.core.assignments.models import (
    Assignment,
    Difficulty,
    TestCase,
    TestCaseKind,
)
from greader.database.core.assignment_repository import SQLAssignmentRepository
from greader.database.session import SessionFactory
from tests.contracts.assignment_repository import AssignmentRepositoryContract

pytestmark = pytest.mark.postgres


class TestSQLAssignmentRepository(AssignmentRepositoryContract):
    """Run the contract against the SQL adapter."""

    @pytest.fixture()
    def repository(
        self, session_factory: SessionFactory, empty_core_tables: None
    ) -> SQLAssignmentRepository:
        return SQLAssignmentRepository(session_factory)


@pytest.mark.usefixtures("empty_core_tables")
def test_test_case_round_trips_through_postgres(
    session_factory: SessionFactory,
) -> None:
    repository = SQLAssignmentRepository(session_factory)

    created = repository.create(
        Assignment(
            title="Sum two numbers",
            problem_statement="Read two ints and print their sum",
            difficulty=Difficulty.EASY,
            metadata={"topic": "arithmetic"},
            test_cases=[
                TestCase(
                    input_data="1 2",
                    expected_output="3",
                    kind=TestCaseKind.HIDDEN,
                    order_index=2,
                )
            ],
        )
    )

    fetched = repository.get(created.id)

    assert fetched is not None
    (test_case,) = fetched.test_cases
    assert test_case.input_data == "1 2"
    assert test_case.expected_output == "3"
    assert test_case.kind is TestCaseKind.HIDDEN
    assert test_case.order_index == 2
    assert fetched.metadata == {"topic": "arithmetic"}


@pytest.mark.usefixtures("empty_core_tables")
def test_deleting_an_assignment_removes_its_test_cases(
    session_factory: SessionFactory,
) -> None:
    repository = SQLAssignmentRepository(session_factory)
    created = repository.create(
        Assignment(
            title="Parent",
            problem_statement="Statement",
            difficulty=Difficulty.EASY,
            test_cases=[TestCase(input_data="1", expected_output="1")],
        )
    )

    assert repository.delete(created.id) is True

    with session_factory() as session:
        remaining = session.execute(
            text("SELECT count(*) FROM core.test_cases WHERE assignment_id = :id"),
            {"id": created.id},
        ).scalar()
    assert remaining == 0


@pytest.mark.usefixtures("empty_core_tables")
def test_list_returns_every_stored_assignment(
    session_factory: SessionFactory,
) -> None:
    repository = SQLAssignmentRepository(session_factory)
    repository.create(
        Assignment(
            title="First",
            problem_statement="Statement",
            difficulty=Difficulty.EASY,
        )
    )
    repository.create(
        Assignment(
            title="Second",
            problem_statement="Statement",
            difficulty=Difficulty.HARD,
        )
    )

    assert [assignment.title for assignment in repository.list()] == [
        "First",
        "Second",
    ]
