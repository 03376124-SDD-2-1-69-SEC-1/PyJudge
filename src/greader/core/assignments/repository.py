from typing import Protocol

from greader.core.assignments.models import Assignment, TestCase


class AssignmentRepository(Protocol):
    def list_all(self) -> list[Assignment]: ...

    def get_by_id(self, assignment_id: int) -> Assignment | None: ...

    def create(self, assignment: Assignment) -> Assignment: ...

    def update(
        self, assignment_id: int, assignment: Assignment
    ) -> Assignment | None: ...

    def delete(self, assignment_id: int) -> bool: ...

    def create_test_case(
        self, assignment_id: int, test_case: TestCase
    ) -> TestCase | None: ...

    def list_test_cases(self, assignment_id: int) -> list[TestCase] | None: ...

    def update_test_case(
        self, assignment_id: int, test_case_id: int, test_case: TestCase
    ) -> TestCase | None: ...

    def delete_test_case(self, assignment_id: int, test_case_id: int) -> bool: ...


class InMemoryAssignmentRepository:
    def __init__(self) -> None:
        self._items: dict[int, Assignment] = {}
        self._next_id: int = 1
        self._next_tc_id: int = 1

    def list_all(self) -> list[Assignment]:
        return list(self._items.values())

    def get_by_id(self, assignment_id: int) -> Assignment | None:
        return self._items.get(assignment_id)

    def create(self, assignment: Assignment) -> Assignment:
        new_id = self._next_id
        self._next_id += 1
        created = Assignment(
            id=new_id,
            title=assignment.title,
            problem_statement=assignment.problem_statement,
            difficulty=assignment.difficulty,
            metadata=assignment.metadata,
            artifact_id=assignment.artifact_id,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
            test_cases=assignment.test_cases or [],
        )
        self._items[new_id] = created
        return created

    def update(self, assignment_id: int, assignment: Assignment) -> Assignment | None:
        if assignment_id not in self._items:
            return None
        existing = self._items[assignment_id]
        updated = Assignment(
            id=assignment_id,
            title=assignment.title,
            problem_statement=assignment.problem_statement,
            difficulty=assignment.difficulty,
            metadata=assignment.metadata,
            artifact_id=assignment.artifact_id,
            created_at=existing.created_at,
            updated_at=assignment.updated_at,
            test_cases=existing.test_cases,
        )
        self._items[assignment_id] = updated
        return updated

    def delete(self, assignment_id: int) -> bool:
        if assignment_id not in self._items:
            return False
        del self._items[assignment_id]
        return True

    def create_test_case(
        self, assignment_id: int, test_case: TestCase
    ) -> TestCase | None:
        assignment = self._items.get(assignment_id)
        if not assignment:
            return None

        tc_id = self._next_tc_id
        self._next_tc_id += 1

        new_tc = TestCase(
            id=tc_id,
            assignment_id=assignment_id,
            input_data=test_case.input_data,
            expected_output=test_case.expected_output,
            is_hidden=test_case.is_hidden,
            weight=test_case.weight,
        )

        updated_tcs = list(assignment.test_cases) + [new_tc]
        self._items[assignment_id] = Assignment(
            id=assignment.id,
            title=assignment.title,
            problem_statement=assignment.problem_statement,
            difficulty=assignment.difficulty,
            metadata=assignment.metadata,
            artifact_id=assignment.artifact_id,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
            test_cases=updated_tcs,
        )
        return new_tc

    def list_test_cases(self, assignment_id: int) -> list[TestCase] | None:
        assignment = self._items.get(assignment_id)
        if not assignment:
            return None
        return assignment.test_cases

    def update_test_case(
        self, assignment_id: int, test_case_id: int, test_case: TestCase
    ) -> TestCase | None:
        assignment = self._items.get(assignment_id)
        if not assignment:
            return None

        tc_index = next(
            (i for i, tc in enumerate(assignment.test_cases) if tc.id == test_case_id),
            None,
        )
        if tc_index is None:
            return None

        existing_tc = assignment.test_cases[tc_index]
        updated_tc = TestCase(
            id=test_case_id,
            assignment_id=assignment_id,
            input_data=test_case.input_data or existing_tc.input_data,
            expected_output=test_case.expected_output or existing_tc.expected_output,
            is_hidden=test_case.is_hidden
            if test_case.is_hidden is not None
            else existing_tc.is_hidden,
            weight=test_case.weight
            if test_case.weight is not None
            else existing_tc.weight,
        )

        updated_tcs = list(assignment.test_cases)
        updated_tcs[tc_index] = updated_tc

        self._items[assignment_id] = Assignment(
            id=assignment.id,
            title=assignment.title,
            problem_statement=assignment.problem_statement,
            difficulty=assignment.difficulty,
            metadata=assignment.metadata,
            artifact_id=assignment.artifact_id,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
            test_cases=updated_tcs,
        )
        return updated_tc

    def delete_test_case(self, assignment_id: int, test_case_id: int) -> bool:
        assignment = self._items.get(assignment_id)
        if not assignment:
            return False

        updated_tcs = [tc for tc in assignment.test_cases if tc.id != test_case_id]
        if len(updated_tcs) == len(assignment.test_cases):
            return False

        self._items[assignment_id] = Assignment(
            id=assignment.id,
            title=assignment.title,
            problem_statement=assignment.problem_statement,
            difficulty=assignment.difficulty,
            metadata=assignment.metadata,
            artifact_id=assignment.artifact_id,
            created_at=assignment.created_at,
            updated_at=assignment.updated_at,
            test_cases=updated_tcs,
        )
        return True
