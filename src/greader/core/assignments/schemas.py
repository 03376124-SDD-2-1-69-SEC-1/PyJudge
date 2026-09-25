"""HTTP contracts for Assignments, Postings, Versions and Test Cases."""

from datetime import datetime

from pydantic import BaseModel, Field

from greader.core.assignments.models import Difficulty, Language, TestCaseKind


class TestCaseBody(BaseModel):
    input_data: str = Field(min_length=1)
    expected_output: str = Field(min_length=1)
    kind: TestCaseKind = TestCaseKind.SAMPLE
    note: str = Field(default="", max_length=120)


class TestCaseWrite(TestCaseBody):
    """Adding or replacing a test case publishes a new Version, so it needs a reason."""

    reason: str = Field(min_length=1, max_length=500)


class TestCaseResponse(BaseModel):
    id: int
    input_data: str
    expected_output: str
    kind: TestCaseKind
    note: str
    order_index: int


class SettingsBody(BaseModel):
    time_limit_ms: int = Field(default=1000, gt=0, le=10_000)
    language: Language = Language.PYTHON3
    show_hidden_names: bool = False


class AssignmentPatch(BaseModel):
    """T-05: fields left out keep their value; every save is a new Version."""

    reason: str = Field(min_length=1, max_length=500)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    problem_statement: str | None = Field(default=None, min_length=1)
    difficulty: Difficulty | None = None
    topic_id: int | None = None
    test_cases: list[TestCaseBody] | None = None
    settings: SettingsBody | None = None
    extend_deadline: dict[int, datetime] = Field(
        default_factory=dict,
        description="Posting id → new deadline, for the Postings ticked in T-05a.",
    )


class AssignmentResponse(BaseModel):
    id: int
    title: str
    problem_statement: str
    difficulty: Difficulty
    topic_id: int | None
    current_version: int
    time_limit_ms: int
    language: Language
    show_hidden_names: bool
    test_cases: list[TestCaseResponse]


class VersionResponse(BaseModel):
    number: int
    title: str
    reason: str
    changed_at: datetime
    test_case_count: int


class PostingPatch(BaseModel):
    deadline: datetime | None = None
    max_score: int | None = Field(default=None, gt=0)
    allow_late: bool | None = None
    allow_resubmission: bool | None = None


class PostingResponse(BaseModel):
    id: int
    classroom_id: int
    assignment_id: int
    deadline: datetime
    max_score: int
    allow_late: bool
    allow_resubmission: bool
    published_at: datetime
    closed_at: datetime | None


class ProblemResponse(BaseModel):
    """A T-01 or S-01 row; `variant` says which numbers are filled."""

    number: int
    title: str
    difficulty: Difficulty
    posting: PostingResponse
    submitted: int | None = None
    avg_score: float | None = None
    state: str | None = None
    score: float | None = None


class ProblemListResponse(BaseModel):
    variant: str
    student_count: int | None
    problems: list[ProblemResponse]


class FailRateResponse(BaseModel):
    title: str
    rate: float


class ScoreRowResponse(BaseModel):
    student_name: str
    scores: list[float | None]
    total: float


class SummaryResponse(BaseModel):
    """T-01 Summary (instructor) or S-01 Summary (student)."""

    variant: str
    student_count: int | None = None
    problem_count: int | None = None
    avg_pass_rate: float | None = None
    never_submitted: int | None = None
    most_failed: list[FailRateResponse] = Field(default_factory=list)
    problem_titles: list[str] = Field(default_factory=list)
    score_table: list[ScoreRowResponse] = Field(default_factory=list)
    solved: int | None = None
    passed: int | None = None
    total: int | None = None
    avg_score: float | None = None
