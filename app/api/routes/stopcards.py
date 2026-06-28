from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_storage, parse_stopcard_payload
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.schemas.stopcard import StopCardCreated, StopCardPayload, ValidationErrorResponse
from app.services.stopcards import create_stopcard
from app.services.storage import ObjectStorage

router = APIRouter(prefix="/stopcards", tags=["stopcards"])


@router.post(
    "",
    response_model=StopCardCreated,
    status_code=status.HTTP_201_CREATED,
    responses={422: {"model": ValidationErrorResponse}},
)
async def submit_stopcard(
    payload: Annotated[StopCardPayload, Depends(parse_stopcard_payload)],
    session: Annotated[AsyncSession, Depends(get_session)],
    storage: Annotated[ObjectStorage, Depends(get_storage)],
    settings: Annotated[Settings, Depends(get_settings)],
    photo: Annotated[UploadFile | None, File()] = None,
    telegram_init_data: Annotated[str | None, Form()] = None,
) -> StopCardCreated:
    return await create_stopcard(
        session=session,
        storage=storage,
        settings=settings,
        payload=payload,
        photo=photo,
        telegram_init_data=telegram_init_data,
    )
