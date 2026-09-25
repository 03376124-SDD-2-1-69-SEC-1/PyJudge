"""Request and response shapes for the submissions API."""

from datetime import datetime

from pydantic import BaseModel, Field

from greader.core.assignments.models import TestCaseKind
from greader.core.submissions.models import Verdict


class CodeRequest(BaseModel):
    code: str = Field(min_length=1)


class TestResultResponse(BaseModel):
    position: int
    kind: TestCaseKind
    verdict: Verdict
    time_seconds: float
    note: str | None = Field(
        description="Hidden and edge tests show a note only to the Instructor "
        "or when the Assignment shows hidden test names."
    )
    expected_output: str | None = Field(description="Sample tests only.")
    actual_output: str | None = Field(description="Sample tests only.")


class SubmissionResponse(BaseModel):
    id: int
    student_id: int
    attempt: int
    version_number: int
    submitted_at: datetime
    is_late: bool
    score: int
    max_score: int
    passed: int
    total: int
    code: str
    results: list[TestResultResponse]


class RunResponse(BaseModel):
    passed: int
    total: int
    results: list[TestResultResponse]
