import pytest

from greader.core.assignments.repository import InMemoryAssignmentRepository
from greader.core.assignments.service import (
    AssignmentNotFoundError,
    AssignmentService,
    TestCaseNotFoundError,
)


def _make_service_with_assignment() -> tuple[AssignmentService, int]:
    service = AssignmentService(InMemoryAssignmentRepository())
    assignment = service.create(
        title="Assignment",
        problem_statement="Solve it",
        difficulty="easy",
    )
    return service, assignment.id or 0


def test_add_test_case_persists_on_the_assignment() -> None:
    service, assignment_id = _make_service_with_assignment()

    created = service.add_test_case(
        assignment_id=assignment_id,
        input_data="1 2",
        expected_output="3",
        is_hidden=False,
        order_index=1,
    )

    assert service.list_test_cases(assignment_id) == [created]
    assert service.get(assignment_id).test_cases == [created]


def test_add_test_case_on_missing_assignment_raises() -> None:
    service = AssignmentService(InMemoryAssignmentRepository())

    with pytest.raises(AssignmentNotFoundError):
        service.add_test_case(
            assignment_id=999,
            input_data="1",
            expected_output="1",
            is_hidden=False,
            order_index=0,
        )


def test_get_missing_test_case_raises() -> None:
    service, assignment_id = _make_service_with_assignment()

    with pytest.raises(TestCaseNotFoundError):
        service.get_test_case(assignment_id, 999)


def test_update_test_case_field_only_preserves_other_fields() -> None:
    service, assignment_id = _make_service_with_assignment()
    created = service.add_test_case(
        assignment_id=assignment_id,
        input_data="1 2",
        expected_output="3",
        is_hidden=False,
        order_index=1,
    )

    updated = service.update_test_case(
        assignment_id=assignment_id,
        test_case_id=created.id or 0,
        is_hidden=True,
    )

    assert updated.is_hidden is True
    assert updated.input_data == "1 2"
    assert updated.expected_output == "3"
    assert updated.order_index == 1


def test_update_test_case_does_not_disturb_other_test_cases() -> None:
    service, assignment_id = _make_service_with_assignment()
    first = service.add_test_case(
        assignment_id=assignment_id,
        input_data="1",
        expected_output="1",
        is_hidden=False,
        order_index=0,
    )
    second = service.add_test_case(
        assignment_id=assignment_id,
        input_data="2",
        expected_output="2",
        is_hidden=False,
        order_index=1,
    )

    service.update_test_case(
        assignment_id=assignment_id, test_case_id=first.id or 0, input_data="1 updated"
    )

    stored = service.list_test_cases(assignment_id)
    assert [tc.id for tc in stored] == [first.id, second.id]
    assert next(tc for tc in stored if tc.id == second.id) == second


def test_delete_test_case_removes_only_that_case() -> None:
    service, assignment_id = _make_service_with_assignment()
    first = service.add_test_case(
        assignment_id=assignment_id,
        input_data="1",
        expected_output="1",
        is_hidden=False,
        order_index=0,
    )
    second = service.add_test_case(
        assignment_id=assignment_id,
        input_data="2",
        expected_output="2",
        is_hidden=False,
        order_index=1,
    )

    deleted = service.delete_test_case(assignment_id, first.id or 0)

    assert deleted is True
    assert service.list_test_cases(assignment_id) == [second]


def test_delete_missing_test_case_returns_false() -> None:
    service, assignment_id = _make_service_with_assignment()

    assert service.delete_test_case(assignment_id, 999) is False


def test_deleting_assignment_removes_its_test_cases() -> None:
    service, assignment_id = _make_service_with_assignment()
    service.add_test_case(
        assignment_id=assignment_id,
        input_data="1",
        expected_output="1",
        is_hidden=False,
        order_index=0,
    )

    service.delete(assignment_id)

    with pytest.raises(AssignmentNotFoundError):
        service.list_test_cases(assignment_id)
