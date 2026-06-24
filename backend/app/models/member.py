"""MemberProfile —— 会员档案，与 User 1:1。"""
from __future__ import annotations

import enum
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class MemberProfile(db.Model):
    __tablename__ = "member_profiles"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    real_name: Mapped[str] = mapped_column(String(64), nullable=False)
    gender: Mapped[Gender | None] = mapped_column(
        Enum(Gender, native_enum=False, length=8, values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    phone: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    birthday: Mapped[date | None] = mapped_column(Date, nullable=True)
    id_card_encrypted: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    emergency_contact: Mapped[str | None] = mapped_column(String(64), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="profile")  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MemberProfile uid={self.user_id} name={self.real_name}>"
