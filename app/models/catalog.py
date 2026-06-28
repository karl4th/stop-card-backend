from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.stopcard import StopCard


class CatalogItem(TimestampMixin, Base):
    __tablename__ = "catalog_items"
    __table_args__ = (
        UniqueConstraint("catalog_type", "code"),
        CheckConstraint(
            "catalog_type IN ('reason', 'circumstance', 'hazard')",
            name="valid_catalog_type",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    catalog_type: Mapped[str] = mapped_column(String(32), index=True)
    code: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(500))
    group_code: Mapped[str | None] = mapped_column(String(64))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    requires_text: Mapped[bool] = mapped_column(Boolean, default=False)


class StopCardStatus(TimestampMixin, Base):
    __tablename__ = "stopcard_statuses"

    code: Mapped[str] = mapped_column(String(32), primary_key=True)
    label: Mapped[str] = mapped_column(String(200))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    is_terminal: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    stopcards: Mapped[list["StopCard"]] = relationship(back_populates="status")
