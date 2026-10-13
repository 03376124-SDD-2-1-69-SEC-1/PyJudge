"""Shared shape of the error envelope documented in OpenAPI."""

from pydantic import BaseModel


class ApplicationErrorDetail(BaseModel):
    """Stable detail shared by explicitly mapped application errors."""

    code: str
    message: str


class ApplicationErrorResponse(BaseModel):
    """Stable envelope shared by explicitly mapped application errors."""

    detail: ApplicationErrorDetail
