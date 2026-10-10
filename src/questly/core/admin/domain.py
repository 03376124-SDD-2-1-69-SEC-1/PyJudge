from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class InstructorRequestStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class UserRole(StrEnum):
    ADMIN = "admin"
    INSTRUCTOR = "instructor"
    STUDENT = "student"


class AISettings(BaseModel):
    model: str = Field(min_length=1)
    daily_quota: int = Field(gt=0)
    max_pages: int = Field(gt=0)
    require_citations: bool
    usage_this_month: int = Field(default=0, ge=0)


class AISettingsUpdate(BaseModel):
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


class ServiceHealthStatus(StrEnum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"


class ServiceStatus(BaseModel):
    name: str
    status: ServiceHealthStatus
    details: str | None = None


class SystemStatusResponse(BaseModel):
    services: list[ServiceStatus]
