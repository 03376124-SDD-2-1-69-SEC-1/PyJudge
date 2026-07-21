"""Assignment domain models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Difficulty(Enum):
    """Assignment difficulty level."""

    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class TestCaseCategory(Enum):
    """Classification of a test case."""

    NORMAL = "Normal"
    BOUNDARY = "Boundary"
    CORNER = "Corner"
    RANDOM = "Random"
    STRESS = "Stress"


class ReviewStatus(Enum):
    """Review status for a test case."""

    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


@dataclass
class TestCase:
    """A single test case for an assignment."""

    id: str
    input_data: str
    expected_output: str
    category: TestCaseCategory
    status: ReviewStatus
    explanation: str
    assignment_id: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Assignment:
    """A programming assignment authored by an instructor."""

    id: str
    title: str
    description: str
    constraints: str
    difficulty: Difficulty
    programming_language: str
    status: str
    reference_solution: str
    test_cases: list[TestCase] = field(default_factory=list)
    ai_suggestions: list[str] = field(default_factory=list)
    coverage_score: float = 0.0
    mutation_score: float = 0.0
    input_format: str = ""
    output_format: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
