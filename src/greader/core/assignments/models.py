from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class TestCase:
    """A single executable test case belonging to an Assignment."""

    id: int | None
    assignment_id: int
    input_data: str
    expected_output: str
    is_hidden: bool = False
    order_index: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Assignment:
    """Domain representation of a programming Assignment."""

    id: int | None
    title: str
    problem_statement: str
    difficulty: str
    metadata: dict[str, Any]
    artifact_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    test_cases: list[TestCase] | None = None
