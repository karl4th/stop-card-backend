from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_admin, get_storage
from app.core.config import Settings, get_settings
from app.core.security import create_access_token, verify_password
from app.db.session import get_session
from app.models import Admin, CatalogItem, StopCard, StopCardStatus
from app.schemas.admin import (
    AdminResponse,
    CatalogItemCreate,
    CatalogItemResponse,
    CatalogItemUpdate,
    LoginRequest,
    PaginatedStopCards,
    PhotoUrlResponse,
    StatusDefinitionResponse,
    StatusDefinitionUpdate,
    StatusUpdate,
    StopCardAdminResponse,
    TokenResponse,
)
from app.services.audit import add_audit_log
from app.services.storage import ObjectStorage

router = APIRouter(prefix="/admin", tags=["admin"])
CatalogType = Literal["reason", "circumstance", "hazard"]


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TokenResponse:
    admin = await session.scalar(select(Admin).where(Admin.username == body.username))
    if (
        admin is None
        or not admin.is_active
        or not verify_password(body.password, admin.password_hash)
    ):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    return TokenResponse(access_token=create_access_token(str(admin.id), settings))


@router.get("/auth/me", response_model=AdminResponse)
async def me(admin: Annotated[Admin, Depends(get_current_admin)]) -> Admin:
    return admin


@router.get("/catalogs/{catalog_type}", response_model=list[CatalogItemResponse])
async def list_catalog(
    catalog_type: CatalogType,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[Admin, Depends(get_current_admin)],
) -> list[CatalogItem]:
    items = await session.scalars(
        select(CatalogItem)
        .where(CatalogItem.catalog_type == catalog_type)
        .order_by(CatalogItem.display_order, CatalogItem.id)
    )
    return list(items)


@router.post(
    "/catalogs/{catalog_type}",
    response_model=CatalogItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_catalog_item(
    catalog_type: CatalogType,
    body: CatalogItemCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[Admin, Depends(get_current_admin)],
) -> CatalogItem:
    item = CatalogItem(catalog_type=catalog_type, **body.model_dump())
    session.add(item)
    try:
        await session.flush()
        add_audit_log(
            session,
            admin=admin,
            action="create",
            entity_type="catalog_item",
            entity_id=str(item.id),
            changes=body.model_dump(mode="json"),
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Код уже существует в справочнике") from exc
    await session.refresh(item)
    return item


@router.get("/statuses", response_model=list[StatusDefinitionResponse])
async def list_statuses(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[Admin, Depends(get_current_admin)],
) -> list[StopCardStatus]:
    statuses = await session.scalars(
        select(StopCardStatus).order_by(StopCardStatus.display_order, StopCardStatus.code)
    )
    return list(statuses)


@router.patch("/statuses/{code}", response_model=StatusDefinitionResponse)
async def update_status(
    code: str,
    body: StatusDefinitionUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[Admin, Depends(get_current_admin)],
) -> StopCardStatus:
    item = await session.get(StopCardStatus, code)
    if item is None:
        raise HTTPException(status_code=404, detail="Статус не найден")
    changes = body.model_dump(exclude_unset=True)
    before = {key: getattr(item, key) for key in changes}
    for key, value in changes.items():
        setattr(item, key, value)
    add_audit_log(
        session,
        admin=admin,
        action="update",
        entity_type="stopcard_status",
        entity_id=item.code,
        changes={"before": before, "after": changes},
    )
    await session.commit()
    await session.refresh(item)
    return item


@router.patch("/catalogs/{catalog_type}/{code}", response_model=CatalogItemResponse)
async def update_catalog_item(
    catalog_type: CatalogType,
    code: str,
    body: CatalogItemUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[Admin, Depends(get_current_admin)],
) -> CatalogItem:
    item = await session.scalar(
        select(CatalogItem).where(
            CatalogItem.catalog_type == catalog_type,
            CatalogItem.code == code,
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Элемент справочника не найден")
    changes = body.model_dump(exclude_unset=True)
    before = {key: getattr(item, key) for key in changes}
    for key, value in changes.items():
        setattr(item, key, value)
    add_audit_log(
        session,
        admin=admin,
        action="update",
        entity_type="catalog_item",
        entity_id=str(item.id),
        changes={"before": before, "after": changes},
    )
    await session.commit()
    await session.refresh(item)
    return item


@router.get("/stopcards", response_model=PaginatedStopCards)
async def list_stopcards(
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[Admin, Depends(get_current_admin)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    status_code: str | None = None,
) -> PaginatedStopCards:
    filters = [StopCard.status_code == status_code] if status_code else []
    total = await session.scalar(select(func.count(StopCard.id)).where(*filters))
    cards = await session.scalars(
        select(StopCard)
        .where(*filters)
        .order_by(StopCard.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return PaginatedStopCards(
        items=[StopCardAdminResponse.model_validate(card) for card in cards],
        total=total or 0,
        page=page,
        page_size=page_size,
    )


@router.get("/stopcards/{stopcard_id}", response_model=StopCardAdminResponse)
async def get_stopcard(
    stopcard_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    _: Annotated[Admin, Depends(get_current_admin)],
) -> StopCard:
    card = await session.get(StopCard, stopcard_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Стопкарта не найдена")
    return card


@router.get("/stopcards/{stopcard_id}/photo-url", response_model=PhotoUrlResponse)
async def get_stopcard_photo_url(
    stopcard_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    storage: Annotated[ObjectStorage, Depends(get_storage)],
    settings: Annotated[Settings, Depends(get_settings)],
    _: Annotated[Admin, Depends(get_current_admin)],
) -> PhotoUrlResponse:
    card = await session.get(StopCard, stopcard_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Стопкарта не найдена")
    if card.photo_object_key is None:
        raise HTTPException(status_code=404, detail="У стопкарты нет фотографии")
    return PhotoUrlResponse(
        url=await storage.public_url(card.photo_object_key),
        expires_in=settings.photo_url_expires_seconds,
    )


@router.patch("/stopcards/{stopcard_id}/status", response_model=StopCardAdminResponse)
async def change_stopcard_status(
    stopcard_id: str,
    body: StatusUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    admin: Annotated[Admin, Depends(get_current_admin)],
) -> StopCard:
    card = await session.get(StopCard, stopcard_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Стопкарта не найдена")
    new_status = await session.get(StopCardStatus, body.status)
    if new_status is None or not new_status.is_active:
        raise HTTPException(status_code=422, detail="Неизвестный или неактивный статус")
    old_status = card.status_code
    card.status_code = body.status
    add_audit_log(
        session,
        admin=admin,
        action="status_change",
        entity_type="stopcard",
        entity_id=card.id,
        changes={"before": old_status, "after": body.status},
    )
    await session.commit()
    await session.refresh(card)
    return card
