"""Booking —— 课程预约。"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class BookingStatus(str, enum.Enum):
    BOOKED = "booked"
    CANCELLED = "cancelled"
    ATTENDED = "attended"
    NO_SHOW = "no_show"


class BookingSource(str, enum.Enum):
    SELF = "self"
    ADMIN = "admin"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Booking(db.Model):
    __tablename__ = "bookings"
    __table_args__ = (
        # SQLite 部分索引：同会员同 session 的"有效"预约（非 cancelled）只能 1 条
        Index(
            "uq_bookings_member_session_active",
            "member_id",
            "session_id",
            unique=True,
            sqlite_where=db.text("status != 'cancelled'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("class_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    card_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("membership_cards.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[BookingStatus] = mapped_column(
        Enum(
            BookingStatus,
            native_enum=False,
            length=16,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=BookingStatus.BOOKED,
    )
    booked_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source: Mapped[BookingSource] = mapped_column(
        Enum(
            BookingSource,
            native_enum=False,
            length=8,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=BookingSource.SELF,
    )

    member = relationship("User", foreign_keys=[member_id])
    session = relationship("ClassSession", back_populates="bookings")
    card = relationship("MembershipCard")
    attendance: Mapped["Attendance | None"] = relationship(  # noqa: F821
        back_populates="booking", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Booking {self.id} m={self.member_id} s={self.session_id} {self.status.value}>"
