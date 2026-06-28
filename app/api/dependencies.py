import json
from functools import lru_cache
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Form, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.errors import FieldValidationError
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models import Admin
from app.schemas.stopcard import StopCardPayload
from app.services.storage import ObjectStorage

bearer = HTTPBearer(auto_error=False)


def _validation_fields(exc: ValidationError) -> dict[str, str]:
    fields: dict[str, str] = {}
    for error in exc.errors(include_url=False):
        path = ".".join(str(item) for item in error["loc"] if item != "__root__") or "payload"
        message = error["msg"]
        if error["type"] in {"missing", "string_too_short", "too_short"}:
            message = "Поле обязательно"
        fields[path] = message
    return fields


async def parse_stopcard_payload(payload: Annotated[str, Form()]) -> StopCardPayload:
    try:
        raw = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise FieldValidationError({"payload": "Некорректный JSON"}) from exc
    try:
        return StopCardPayload.model_validate(raw)
    except ValidationError as exc:
        raise FieldValidationError(_validation_fields(exc)) from exc


@lru_cache
def get_storage() -> ObjectStorage:
    return ObjectStorage(get_settings())


async def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Admin:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Недействительные учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        admin_id = decode_access_token(credentials.credentials, settings)
        parsed_admin_id = UUID(admin_id)
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise unauthorized from exc

    admin = await session.scalar(select(Admin).where(Admin.id == parsed_admin_id))
    if admin is None or not admin.is_active:
        raise unauthorized
    return admin
