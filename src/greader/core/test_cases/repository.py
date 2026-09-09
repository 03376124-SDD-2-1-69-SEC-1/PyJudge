"""Repository port and in-memory adapter for Test Cases."""

from typing import Protocol

from greader.core.test_cases.models import TestCase


class TestCaseRepository(Protocol):
    """Persistence operations required by TestCaseService."""

    def create_test_case(self, test_case: TestCase) -> TestCase: ...

    def list_test_cases(self, assignment_id: int) -> list[TestCase]: ...

    def get_test_case(
        self, assignment_id: int, test_case_id: int
    ) -> TestCase | None: ...

    def update_test_case(
        self, assignment_id: int, test_case_id: int, test_case: TestCase
    ) -> TestCase | None: ...

    def delete_test_case(self, assignment_id: int, test_case_id: int) -> bool: ...


class InMemoryTestCaseRepository:
    """Store Test Cases in process for isolated application instances."""

    def __init__(self) -> None:
        """Initialize an empty Test Case repository."""
        self._items: dict[tuple[int, int], TestCase] = {}
        self._next_id = 1

    def create_test_case(self, test_case: TestCase) -> TestCase:
        """Store a Test Case with a generated id."""
        test_case_id = self._next_id
        self._next_id += 1
        created = TestCase(
            id=test_case_id,
            assignment_id=test_case.assignment_id,
            input_data=test_case.input_data,
            expected_output=test_case.expected_output,
            is_hidden=test_case.is_hidden,
            order_index=test_case.order_index,
        )
        self._items[(created.assignment_id, test_case_id)] = created
        return created

    def list_test_cases(self, assignment_id: int) -> list[TestCase]:
        """Return Test Cases for one Assignment in insertion order."""
        return [
            test_case
            for (stored_assignment_id, _), test_case in self._items.items()
            if stored_assignment_id == assignment_id
        ]

    def get_test_case(
        self, assignment_id: int, test_case_id: int
    ) -> TestCase | None:
        """Return one Test Case when it belongs to the Assignment."""
        return self._items.get((assignment_id, test_case_id))

    def update_test_case(
        self, assignment_id: int, test_case_id: int, test_case: TestCase
    ) -> TestCase | None:
        """Replace one stored Test Case."""
        key = (assignment_id, test_case_id)
        if key not in self._items:
            return None
        self._items[key] = test_case
        return test_case

    def delete_test_case(self, assignment_id: int, test_case_id: int) -> bool:
        """Delete exactly one Test Case when it exists."""
        key = (assignment_id, test_case_id)
        if key not in self._items:
            return False
        del self._items[key]
        return True
