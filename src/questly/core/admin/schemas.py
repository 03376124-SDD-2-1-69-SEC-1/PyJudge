from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from questly.core.admin.models import ServiceHealthStatus
from questly.core.auth.models import InstructorRequestStatus, Role


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
    role: Role = Field(..., description="Role ใหม่ที่จะตั้งให้ผู้ใช้")


class AISettingsUpdate(BaseModel):
    """PUT body: send only the fields to change; null is rejected."""

    model: str | None = Field(default=None, min_length=1)
    daily_quota: int | None = Field(default=None, gt=0)
    max_pages: int | None = Field(default=None, gt=0)
    require_citations: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_values(cls, value: object) -> object:
        if isinstance(value, dict) and any(item is None for item in value.values()):
            raise ValueError("Omit unchanged AI settings instead of sending null")
        return value


class AISettingsResponse(BaseModel):
    model: str
    daily_quota: int
    max_pages: int
    require_citations: bool
    usage_this_month: int = Field(ge=0)


class ServiceStatusResponse(BaseModel):
    name: str
    status: ServiceHealthStatus
    details: str | None = None


class SystemStatusResponse(BaseModel):
    services: list[ServiceStatusResponse]
