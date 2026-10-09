from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from questly.core.admin.domain import UserRole
from questly.core.auth.models import InstructorRequestStatus


class InstructorRequestResponse(BaseModel):
    id: int
    user_id: int
    full_name: str
    email: EmailStr
    faculty: str
    status: InstructorRequestStatus
    reviewed_by: int | None = None
    reviewed_at: datetime | None = None
    requested_at: datetime


class UserAdminResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: str
    is_active: bool


class UserPaginatedResponse(BaseModel):
    items: list[UserAdminResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(default=25, ge=1, le=25)


class UserRoleUpdate(BaseModel):
    role: UserRole = Field(..., description="Role ใหม่ที่จะตั้งให้ผู้ใช้")
