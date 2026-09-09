"""Test Case domain model."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TestCase:
    """An executable input/output example belonging to an Assignment."""

    id: int | None
    assignment_id: int
    input_data: str
    expected_output: str
    is_hidden: bool = False
    order_index: int = 0
