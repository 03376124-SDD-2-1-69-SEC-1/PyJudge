from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class TestCase:
    id: int | None = None
    assignment_id: int | None = None
    input_data: str = ""
    expected_output: str = ""
    is_hidden: bool = False
    weight: float = 1.0
    order_index: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Assignment:
    id: int | None = None
    title: str = ""
    problem_statement: str = ""
    difficulty: str = "easy"
    metadata: dict[str, object] = field(default_factory=dict)
    artifact_id: int | None = None
    created_at: datetime | None = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime | None = field(default_factory=lambda: datetime.now(UTC))
    test_cases: list[TestCase] = field(default_factory=list)
