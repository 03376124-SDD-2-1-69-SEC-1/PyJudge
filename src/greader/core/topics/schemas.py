"""HTTP contracts for the Topic reference API."""

from pydantic import BaseModel, Field, field_validator


class TopicWrite(BaseModel):
    """Fields accepted when a client creates or replaces a Topic."""

    name: str = Field(max_length=80)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class TopicCreate(TopicWrite):
    """Request body for creating a Topic."""


class TopicReplace(TopicWrite):
    """Request body for replacing a Topic."""


class TopicPatch(BaseModel):
    """Request body for updating some fields of a Topic.

    A field left out of the JSON body keeps the Topic's current value. Only a
    field present in the body is applied, so ``model_fields_set`` is how the
    route tells "left out" apart from "sent as null".
    """

    name: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=500)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("name must not be null")
        value = value.strip()
        if not value:
            raise ValueError("name must not be blank")
        return value

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class TopicResponse(BaseModel):
    """Public representation returned by the Topic API."""

    id: str
    name: str
    description: str | None
