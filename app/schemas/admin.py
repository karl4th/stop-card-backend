from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str


class CatalogItemCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    code: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")
    label: str = Field(min_length=1, max_length=500)
    group_code: str | None = Field(default=None, max_length=64)
    display_order: int = 0
    is_active: bool = True
    requires_text: bool = False


class CatalogItemUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    label: str | None = Field(default=None, min_length=1, max_length=500)
    group_code: str | None = Field(default=None, max_length=64)
    display_order: int | None = None
    is_active: bool | None = None
    requires_text: bool | None = None


class CatalogItemResponse(CatalogItemCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    catalog_type: Literal["reason", "circumstance", "hazard"]
    created_at: datetime
    updated_at: datetime


class StatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=32)


class StatusDefinitionUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    label: str | None = Field(default=None, min_length=1, max_length=200)
    display_order: int | None = None
    is_terminal: bool | None = None
    is_active: bool | None = None


class StatusDefinitionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    label: str
    display_order: int
    is_terminal: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class StopCardAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status_code: str
    author_last_name: str
    author_first_name: str
    author_patronymic: str | None
    worker_full_name: str
    worker_department: str
    worker_object: str
    reason_code: str
    circumstance_codes: list[str]
    description: str
    hazard_codes: list[str]
    hazard_other_text: str | None
    corrective: str
    telegram_user_id: int | None
    telegram_username: str | None
    photo_object_key: str | None
    photo_content_type: str | None
    photo_size: int | None
    created_at: datetime
    updated_at: datetime


class PaginatedStopCards(BaseModel):
    items: list[StopCardAdminResponse]
    total: int
    page: int
    page_size: int


class PhotoUrlResponse(BaseModel):
    url: str
    expires_in: int
