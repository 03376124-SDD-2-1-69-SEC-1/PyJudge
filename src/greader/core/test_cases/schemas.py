from pydantic import BaseModel, Field


class TestCaseCreate(BaseModel):
    input_data: str = Field(..., min_length=1)
    expected_output: str = Field(..., min_length=1)
    is_hidden: bool = False
    order_index: int = 0


class TestCaseUpdate(BaseModel):
    input_data: str | None = Field(default=None, min_length=1)
    expected_output: str | None = Field(default=None, min_length=1)
    is_hidden: bool | None = None
    order_index: int | None = None


class TestCaseResponse(BaseModel):
    id: int
    assignment_id: int
    input_data: str
    expected_output: str
    is_hidden: bool
    order_index: int
