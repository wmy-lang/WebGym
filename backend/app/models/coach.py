"""Coach —— 教练。"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db
from .member import Gender


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Coach(db.Model):
    __tablename__ = "coaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    gender: Mapped[Gender | None] = mapped_column(
        Enum(Gender, native_enum=False, length=8, values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    specialty: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    hired_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Coach {self.id} {self.name}>"
