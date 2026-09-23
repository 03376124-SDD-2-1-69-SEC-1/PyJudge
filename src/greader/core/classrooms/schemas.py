"""HTTP contracts for /api/v1/classrooms."""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator


def _not_blank(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value


class ClassroomCreate(BaseModel):
    course_code: str = Field(max_length=20)
    course_name: str = Field(max_length=120)
    section: str = Field(max_length=10)
    semester: str = Field(max_length=20)

    @field_validator("course_code", "course_name", "section", "semester")
    @classmethod
    def must_not_be_blank(cls, value: str) -> str:
        return _not_blank(value)


class ClassroomPatch(BaseModel):
    """Only fields present in the body change; see `model_fields_set`."""

    course_code: str | None = Field(default=None, max_length=20)
    course_name: str | None = Field(default=None, max_length=120)
    section: str | None = Field(default=None, max_length=10)
    semester: str | None = Field(default=None, max_length=20)

    @field_validator("course_code", "course_name", "section", "semester")
    @classmethod
    def must_not_be_null_or_blank(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("must not be null")
        return _not_blank(value)


class JoinRequest(BaseModel):
    join_code: str = Field(max_length=20)


class ClassroomResponse(BaseModel):
    id: int
    course_code: str
    course_name: str
    section: str
    semester: str
    archived: bool
    join_code: str | None = Field(
        description="Shown to the owning Instructor only; null for Members."
    )


class InstructorCardResponse(BaseModel):
    classroom: ClassroomResponse
    student_count: int
    problem_count: int
    draft_count: int
    avg_pass_rate: float | None


class StudentCardResponse(BaseModel):
    classroom: ClassroomResponse
    instructor_name: str
    pending_count: int
    next_deadline: datetime | None


class StudentProgressResponse(BaseModel):
    solved: int
    total: int
    passed: int


class PickerResponse(BaseModel):
    """C-01. `variant` says which card list is filled."""

    variant: str
    instructor_cards: list[InstructorCardResponse]
    student_cards: list[StudentCardResponse]
    progress: StudentProgressResponse | None


class MemberResponse(BaseModel):
    user_id: int
    full_name: str
    email: str
    student_number: str | None
    joined_at: datetime
