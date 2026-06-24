"""课程相关：ClassDefinition（课程定义）+ ClassSession（一次具体排课）。"""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class SessionStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    FINISHED = "finished"


class ClassDefinition(db.Model):
    __tablename__ = "class_definitions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    coach_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("coaches.id", ondelete="SET NULL"), nullable=True
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    coach = relationship("Coach")
    sessions: Mapped[list["ClassSession"]] = relationship(back_populates="class_def")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ClassDefinition {self.name}>"


class ClassSession(db.Model):
    __tablename__ = "class_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    class_def_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("class_definitions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    coach_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("coaches.id", ondelete="SET NULL"), nullable=True
    )

    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    location: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[SessionStatus] = mapped_column(
        Enum(
            SessionStatus,
            native_enum=False,
            length=16,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=SessionStatus.SCHEDULED,
    )

    class_def = relationship("ClassDefinition", back_populates="sessions")
    coach = relationship("Coach")
    bookings: Mapped[list["Booking"]] = relationship(  # noqa: F821
        back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ClassSession {self.id} {self.start_at.isoformat()}>"
