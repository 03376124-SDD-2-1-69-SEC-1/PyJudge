"""Request and response schemas for the Assignment API.

Write shapes follow the Topics slice: `PUT` takes a full replacement and `PATCH`
takes only the fields present in the body. A single all-optional schema behind
`PUT` served PATCH semantics under the wrong verb.
"""

from pydantic import BaseModel, Field

from greader.core.assignments.models import Difficulty


class AssignmentCreate(BaseModel):
    """Fields required to create an Assignment."""

    title: str = Field(..., min_length=1)
    problem_statement: str = Field(..., min_length=1)
    difficulty: Difficulty
    metadata: dict[str, object] = Field(default_factory=dict)


class AssignmentReplace(BaseModel):
    """Full replacement body for an existing Assignment."""

    title: str = Field(..., min_length=1)
    problem_statement: str = Field(..., min_length=1)
    difficulty: Difficulty
    metadata: dict[str, object] = Field(default_factory=dict)


class AssignmentPatch(BaseModel):
    """Partial update body: a field left out keeps its stored value."""

    title: str | None = Field(default=None, min_length=1)
    problem_statement: str | None = Field(default=None, min_length=1)
    difficulty: Difficulty | None = None
    metadata: dict[str, object] | None = None


class AssignmentResponse(BaseModel):
    """Public representation of an Assignment returned by the API."""

    id: int
    title: str
    problem_statement: str
    difficulty: Difficulty
    metadata: dict[str, object] = Field(default_factory=dict)
    artifact_id: int | None = None


class TestCaseCreate(BaseModel):
    """Fields required to create a TestCase on an Assignment."""

    input_data: str = Field(..., min_length=1)
    expected_output: str = Field(..., min_length=1)
    is_hidden: bool = False
    order_index: int = 0


class TestCaseReplace(BaseModel):
    """Full replacement body for an existing TestCase."""

    input_data: str = Field(..., min_length=1)
    expected_output: str = Field(..., min_length=1)
    is_hidden: bool = False
    order_index: int = 0


class TestCasePatch(BaseModel):
    """Partial update body: a field left out keeps its stored value."""

    input_data: str | None = Field(default=None, min_length=1)
    expected_output: str | None = Field(default=None, min_length=1)
    is_hidden: bool | None = None
    order_index: int | None = None


class TestCaseResponse(BaseModel):
    """Public representation of a TestCase returned by the API."""

    id: int
    input_data: str
    expected_output: str
    is_hidden: bool
    order_index: int
