"""Mapping functions between ORM records and domain models."""

from greader.assignments.models import (
    Assignment,
    Difficulty,
    ReviewStatus,
    TestCase,
    TestCaseCategory,
)
from greader.db_models import AssignmentRecord, TestCaseRecord

# ---------------------------------------------------------------------------
# TestCase mapping
# ---------------------------------------------------------------------------


def test_case_record_to_domain(record: TestCaseRecord) -> TestCase:
    """Convert a :class:`TestCaseRecord` to a domain :class:`TestCase`."""
    return TestCase(
        id=record.id,
        input_data=record.input_data,
        expected_output=record.expected_output,
        category=TestCaseCategory(record.category),
        status=ReviewStatus(record.status),
        explanation=record.explanation,
        assignment_id=record.assignment_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def test_case_domain_to_record(
    domain: TestCase,
    assignment_id: str,
) -> TestCaseRecord:
    """Convert a domain :class:`TestCase` to a :class:`TestCaseRecord`."""
    return TestCaseRecord(
        id=domain.id,
        assignment_id=assignment_id,
        input_data=domain.input_data,
        expected_output=domain.expected_output,
        category=domain.category.value,
        status=domain.status.value,
        explanation=domain.explanation,
    )


# ---------------------------------------------------------------------------
# Assignment mapping
# ---------------------------------------------------------------------------


def assignment_record_to_domain(record: AssignmentRecord) -> Assignment:
    """Convert an :class:`AssignmentRecord` to a domain :class:`Assignment`."""
    return Assignment(
        id=record.id,
        title=record.title,
        description=record.description,
        input_format=record.input_format,
        output_format=record.output_format,
        constraints=record.constraints,
        difficulty=Difficulty(record.difficulty),
        programming_language=record.programming_language,
        status=record.status,
        reference_solution=record.reference_solution,
        coverage_score=record.coverage_score,
        mutation_score=record.mutation_score,
        created_at=record.created_at,
        updated_at=record.updated_at,
        test_cases=[test_case_record_to_domain(tc) for tc in record.test_cases],
    )


def assignment_domain_to_record(domain: Assignment) -> AssignmentRecord:
    """Convert a domain :class:`Assignment` to an :class:`AssignmentRecord`."""
    record = AssignmentRecord(
        id=domain.id,
        title=domain.title,
        description=domain.description,
        input_format=domain.input_format,
        output_format=domain.output_format,
        constraints=domain.constraints,
        difficulty=domain.difficulty.value,
        programming_language=domain.programming_language,
        status=domain.status,
        reference_solution=domain.reference_solution,
        coverage_score=domain.coverage_score,
        mutation_score=domain.mutation_score,
    )
    record.test_cases = [
        test_case_domain_to_record(tc, domain.id) for tc in domain.test_cases
    ]
    return record
