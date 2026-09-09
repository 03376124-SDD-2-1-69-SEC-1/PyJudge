"""HTTP-contract schemas for Test Cases."""

from pydantic import BaseModel, Field


class TestCaseCreate(BaseModel):
    """Fields required to create a Test Case."""

    input_data: str = Field(..., min_length=1)
    expected_output: str = Field(..., min_length=1)
    is_hidden: bool = False
    order_index: int = 0


class TestCaseUpdate(BaseModel):
    """Optional fields for a partial Test Case update."""

    input_data: str | None = Field(default=None, min_length=1)
    expected_output: str | None = Field(default=None, min_length=1)
    is_hidden: bool | None = None
    order_index: int | None = None


class TestCaseResponse(BaseModel):
    """Public representation of a Test Case."""

    id: int
    assignment_id: int
    input_data: str
    expected_output: str
    is_hidden: bool
    order_index: int

    model_config = {"from_attributes": True}
