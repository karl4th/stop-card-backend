from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

RequiredText = Annotated[str, Field(min_length=1, max_length=500)]


class TrimmedModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, str_strip_whitespace=True, extra="forbid")


class AuthorPayload(TrimmedModel):
    last_name: RequiredText = Field(alias="lastName")
    first_name: RequiredText = Field(alias="firstName")
    patronymic: str | None = Field(default=None, alias="patronymic", max_length=200)

    @field_validator("patronymic")
    @classmethod
    def empty_to_none(cls, value: str | None) -> str | None:
        return value or None


class WorkerPayload(TrimmedModel):
    full_name: RequiredText = Field(alias="fullName", max_length=300)
    department: RequiredText = Field(max_length=300)
    object: RequiredText = Field(max_length=300)


class ReasonPayload(TrimmedModel):
    reason: RequiredText = Field(max_length=64)


class SelectionPayload(TrimmedModel):
    selected: list[Annotated[str, Field(min_length=1, max_length=64)]] = Field(
        min_length=1, max_length=50
    )

    @field_validator("selected")
    @classmethod
    def selections_must_be_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Элементы не должны повторяться")
        return value


class TextPayload(TrimmedModel):
    text: RequiredText = Field(max_length=10_000)


class HazardsPayload(SelectionPayload):
    other_text: str | None = Field(
        default=None, alias="otherText", max_length=2000, validate_default=True
    )

    @field_validator("other_text")
    @classmethod
    def normalize_and_validate_other_text(
        cls, value: str | None, info: ValidationInfo
    ) -> str | None:
        normalized = value or None
        if "other" in info.data.get("selected", []) and not normalized:
            raise ValueError("Поле обязательно при выборе other")
        return normalized


class StopCardPayload(TrimmedModel):
    author: AuthorPayload
    worker: WorkerPayload
    reason: ReasonPayload
    circumstances: SelectionPayload
    description: TextPayload
    hazards: HazardsPayload
    corrective: TextPayload


class StopCardCreated(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    status: str
    created_at: datetime = Field(alias="createdAt")
    photo_url: str | None = Field(alias="photoUrl")


class ValidationErrorResponse(BaseModel):
    error: str = "validation_error"
    fields: dict[str, str]
