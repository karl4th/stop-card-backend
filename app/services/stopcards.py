from datetime import UTC

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from app.core.config import Settings
from app.core.errors import FieldValidationError
from app.models import CatalogItem, StopCard
from app.schemas.stopcard import StopCardCreated, StopCardPayload
from app.services.storage import ObjectStorage, PhotoValidationError, validate_photo
from app.services.telegram import TelegramAuthError, TelegramIdentity, validate_telegram_init_data


async def _validate_catalog_codes(session: AsyncSession, payload: StopCardPayload) -> None:
    requested = {
        "reason": {payload.reason.reason},
        "circumstance": set(payload.circumstances.selected),
        "hazard": set(payload.hazards.selected),
    }
    rows = await session.scalars(
        select(CatalogItem).where(
            CatalogItem.is_active.is_(True),
            CatalogItem.catalog_type.in_(requested),
        )
    )
    existing: dict[str, set[str]] = {key: set() for key in requested}
    requires_text: dict[str, set[str]] = {key: set() for key in requested}
    for row in rows:
        existing[row.catalog_type].add(row.code)
        if row.requires_text:
            requires_text[row.catalog_type].add(row.code)

    fields: dict[str, str] = {}
    paths = {
        "reason": "reason.reason",
        "circumstance": "circumstances.selected",
        "hazard": "hazards.selected",
    }
    for catalog_type, codes in requested.items():
        unknown = codes - existing[catalog_type]
        if unknown:
            fields[paths[catalog_type]] = (
                f"Неизвестные или неактивные значения: {', '.join(sorted(unknown))}"
            )

    if requires_text["hazard"] & requested["hazard"] and not payload.hazards.other_text:
        fields["hazards.otherText"] = "Поле обязательно для выбранного опасного фактора"
    if fields:
        raise FieldValidationError(fields)


def _telegram_identity(init_data: str | None, settings: Settings) -> TelegramIdentity | None:
    if not init_data:
        return None
    try:
        return validate_telegram_init_data(
            init_data,
            settings.telegram_bot_token,
            max_age_seconds=settings.telegram_auth_max_age_seconds,
            future_skew_seconds=settings.telegram_auth_future_skew_seconds,
        )
    except TelegramAuthError as exc:
        raise FieldValidationError({"telegram_init_data": str(exc)}) from exc


async def create_stopcard(
    *,
    session: AsyncSession,
    storage: ObjectStorage,
    settings: Settings,
    payload: StopCardPayload,
    photo: UploadFile | None,
    telegram_init_data: str | None,
) -> StopCardCreated:
    await _validate_catalog_codes(session, payload)
    telegram = _telegram_identity(telegram_init_data, settings)

    stopcard_id = str(ULID())
    photo_key: str | None = None
    photo_type: str | None = None
    photo_size: int | None = None
    photo_url: str | None = None

    if photo is not None:
        raw = await photo.read(settings.photo_max_bytes + 1)
        try:
            validated = validate_photo(raw, photo.content_type, settings.photo_max_bytes)
        except PhotoValidationError as exc:
            raise FieldValidationError({"photo": str(exc)}) from exc
        photo_key = f"stopcards/{stopcard_id}/photo{validated.extension}"
        photo_type = validated.content_type
        photo_size = len(validated.data)
        await storage.ensure_bucket()
        await storage.upload(photo_key, validated)
        try:
            photo_url = await storage.public_url(photo_key)
        except Exception:
            await storage.delete(photo_key)
            raise

    card = StopCard(
        id=stopcard_id,
        status_code="created",
        author_last_name=payload.author.last_name,
        author_first_name=payload.author.first_name,
        author_patronymic=payload.author.patronymic,
        worker_full_name=payload.worker.full_name,
        worker_department=payload.worker.department,
        worker_object=payload.worker.object,
        reason_code=payload.reason.reason,
        circumstance_codes=payload.circumstances.selected,
        description=payload.description.text,
        hazard_codes=payload.hazards.selected,
        hazard_other_text=payload.hazards.other_text,
        corrective=payload.corrective.text,
        telegram_user_id=telegram.user_id if telegram else None,
        telegram_username=telegram.username if telegram else None,
        telegram_auth_date=telegram.auth_date if telegram else None,
        telegram_user_snapshot=telegram.user if telegram else None,
        photo_object_key=photo_key,
        photo_content_type=photo_type,
        photo_size=photo_size,
    )
    session.add(card)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        if photo_key:
            await storage.delete(photo_key)
        raise
    await session.refresh(card)

    created_at = card.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return StopCardCreated(
        id=card.id,
        status=card.status_code,
        createdAt=created_at,
        photoUrl=photo_url,
    )
