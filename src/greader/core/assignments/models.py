"""Domain representation of an Assignment and its embedded TestCases."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TestCase:
    """A single executable test case belonging to an Assignment."""

    input_data: str
    expected_output: str
    id: int | None = None
    is_hidden: bool = False
    order_index: int = 0


@dataclass(frozen=True, slots=True)
class Assignment:
    """Domain representation of a programming Assignment.

    Test cases are generated, reviewed, and approved together with their
    Assignment, so they live on this aggregate rather than as a separate
    root — see docs/task-scope.md for the CORE-04/CORE-05 integration.

    `id` is `None` only before the repository has persisted the entity —
    see AssignmentRepository.create(). Anything a repository returns has a
    non-None id.
    """

    title: str
    problem_statement: str
    difficulty: str
    id: int | None = None
    metadata: dict[str, object] = field(default_factory=dict)
    artifact_id: int | None = None
    test_cases: list[TestCase] = field(default_factory=list)
