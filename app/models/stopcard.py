from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class StopCard(TimestampMixin, Base):
    __tablename__ = "stopcards"
    __table_args__ = (
        Index("ix_stopcards_status_created_at", "status_code", "created_at"),
        Index("ix_stopcards_telegram_user_id", "telegram_user_id"),
    )

    id: Mapped[str] = mapped_column(String(26), primary_key=True)
    status_code: Mapped[str] = mapped_column(
        ForeignKey("stopcard_statuses.code"), default="created", index=True
    )

    author_last_name: Mapped[str] = mapped_column(String(200))
    author_first_name: Mapped[str] = mapped_column(String(200))
    author_patronymic: Mapped[str | None] = mapped_column(String(200))
    worker_full_name: Mapped[str] = mapped_column(String(300))
    worker_department: Mapped[str] = mapped_column(String(300))
    worker_object: Mapped[str] = mapped_column(String(300))
    reason_code: Mapped[str] = mapped_column(String(64), index=True)
    circumstance_codes: Mapped[list[str]] = mapped_column(JSON)
    description: Mapped[str] = mapped_column(Text)
    hazard_codes: Mapped[list[str]] = mapped_column(JSON)
    hazard_other_text: Mapped[str | None] = mapped_column(Text)
    corrective: Mapped[str] = mapped_column(Text)

    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)
    telegram_username: Mapped[str | None] = mapped_column(String(100))
    telegram_auth_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    telegram_user_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    photo_object_key: Mapped[str | None] = mapped_column(String(500))
    photo_content_type: Mapped[str | None] = mapped_column(String(100))
    photo_size: Mapped[int | None]

    status: Mapped["StopCardStatus"] = relationship(back_populates="stopcards")


from app.models.catalog import StopCardStatus  # noqa: E402
