"""User —— 系统账号（admin / staff / member 三种角色）。"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from werkzeug.security import check_password_hash, generate_password_hash

from ..extensions import db


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    STAFF = "staff"
    MEMBER = "member"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(db.Model, UserMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=16, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=UserRole.MEMBER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    profile: Mapped["MemberProfile | None"] = relationship(  # noqa: F821
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def set_password(self, raw: str) -> None:
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        return check_password_hash(self.password_hash, raw)

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def is_staff(self) -> bool:
        return self.role in (UserRole.ADMIN, UserRole.STAFF)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.id} {self.username} role={self.role.value}>"
