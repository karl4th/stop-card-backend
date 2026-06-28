from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models import CatalogItem

router = APIRouter(prefix="/reference", tags=["reference"])


class ReferenceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    label: str
    group_code: str | None
    display_order: int
    requires_text: bool


@router.get("/{catalog_type}", response_model=list[ReferenceItem])
async def list_reference_items(
    catalog_type: Literal["reason", "circumstance", "hazard"],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[CatalogItem]:
    result = await session.scalars(
        select(CatalogItem)
        .where(
            CatalogItem.catalog_type == catalog_type,
            CatalogItem.is_active.is_(True),
        )
        .order_by(CatalogItem.display_order, CatalogItem.id)
    )
    return list(result)
