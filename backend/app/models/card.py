"""会员卡相关：CardType（卡种字典）+ MembershipCard（卡实例）。"""
from __future__ import annotations

import enum
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..extensions import db


class CardStatus(str, enum.Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CardType(db.Model):
    __tablename__ = "card_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # duration_days 与 total_visits 至少一个有值；约束放 service 层校验
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_visits: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    cards: Mapped[list["MembershipCard"]] = relationship(back_populates="card_type")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CardType {self.name}>"


class MembershipCard(db.Model):
    __tablename__ = "membership_cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)

    member_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    card_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("card_types.id", ondelete="RESTRICT"), nullable=False
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    remaining_visits: Mapped[int | None] = mapped_column(Integer, nullable=True)

    status: Mapped[CardStatus] = mapped_column(
        Enum(
            CardStatus,
            native_enum=False,
            length=16,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=CardStatus.ACTIVE,
    )

    issued_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    member = relationship("User", foreign_keys=[member_id])
    issuer = relationship("User", foreign_keys=[issued_by])
    card_type = relationship("CardType", back_populates="cards")

    def is_usable_on(self, when: date) -> bool:
        """业务可用：状态 active、未过期、（次卡）次数 > 0。"""
        if self.status != CardStatus.ACTIVE:
            return False
        if self.end_date is not None and when > self.end_date:
            return False
        if self.remaining_visits is not None and self.remaining_visits <= 0:
            return False
        return True

    def __repr__(self) -> str:  # pragma: no cover
        return f"<MembershipCard {self.card_no} {self.status.value}>"
