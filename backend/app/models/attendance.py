"""Attendance —— 课程签到。"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Attendance(db.Model):
    __tablename__ = "attendances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("bookings.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    checked_in_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    checked_in_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    booking = relationship("Booking", back_populates="attendance")
    operator = relationship("User", foreign_keys=[checked_in_by])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Attendance b={self.booking_id} @{self.checked_in_at.isoformat()}>"
