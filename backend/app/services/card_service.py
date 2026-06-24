"""办卡 / 续费 / 冻结 业务规则。对照 Spring `@Service`。

状态机（见 docs/数据库设计.md §状态机）：

    issue ──▶ active ──freeze──▶ frozen
                ▲     ◀─unfreeze──┘
                │
                ├──expire(自动 / 定时)──▶ expired
                └──cancel─────────────▶ cancelled

业务约束：
- 同会员同一时刻最多一张 ``active`` 卡（同种 + 同时段不能并存）；不同卡种允许并存 → 简化版：直接允许并存，UI 选择优先卡
- ``CardType.duration_days``：续费按"以原 end_date 或今天孰大 + duration_days"延长
- ``CardType.total_visits``：续费按 ``remaining_visits + total_visits``
- 取消 / 冻结后不可再回 active（cancel 是终态；frozen 只能 unfreeze）

card_no 由本模块生成：``C`` + 日期 + 6 位序号（同日内自增），不依赖外部。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from ..extensions import db
from ..models import CardStatus, CardType, MembershipCard, User, UserRole


class CardError(Exception):
    """业务异常基类。``code`` 给路由层做成 4xx 错误码。"""

    def __init__(self, code: str, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


@dataclass
class IssueInput:
    member_id: int
    card_type_id: int
    start_date: date | None = None  # 默认今天
    issued_by_id: int | None = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return datetime.now().date()


def _generate_card_no() -> str:
    """C + YYYYMMDD + 6 位日内序号。SQLite 串行写没有竞争。"""
    today = _today()
    prefix = f"C{today.strftime('%Y%m%d')}"
    latest = db.session.scalar(
        select(MembershipCard.card_no)
        .where(MembershipCard.card_no.like(f"{prefix}%"))
        .order_by(MembershipCard.id.desc())
        .limit(1)
    )
    seq = 1 if latest is None else int(latest[len(prefix) :]) + 1
    return f"{prefix}{seq:06d}"


def _compute_end_date(card_type: CardType, start: date) -> date | None:
    if card_type.duration_days is None:
        return None
    return start + timedelta(days=card_type.duration_days)


def _assert_member(member_id: int) -> User:
    user = db.session.get(User, member_id)
    if user is None or user.role != UserRole.MEMBER:
        raise CardError("member_not_found", status_code=404)
    if not user.is_active:
        raise CardError("member_disabled", status_code=400)
    return user


def _assert_card_type(card_type_id: int) -> CardType:
    ct = db.session.get(CardType, card_type_id)
    if ct is None or not ct.is_active:
        raise CardError("card_type_not_found", status_code=404)
    return ct


def issue_card(data: IssueInput) -> MembershipCard:
    """开新卡。"""
    _assert_member(data.member_id)
    ct = _assert_card_type(data.card_type_id)

    start = data.start_date or _today()
    card = MembershipCard(
        card_no=_generate_card_no(),
        member_id=data.member_id,
        card_type_id=ct.id,
        start_date=start,
        end_date=_compute_end_date(ct, start),
        remaining_visits=ct.total_visits,
        status=CardStatus.ACTIVE,
        issued_by=data.issued_by_id,
        issued_at=_utcnow(),
    )
    db.session.add(card)
    db.session.commit()
    return card


def renew_card(card_id: int) -> MembershipCard:
    """续费：按当前卡的卡种续。

    - 期限卡：end_date = max(end_date, today) + duration_days
    - 次卡：  remaining_visits += total_visits
    - cancelled 卡不允许续；expired 续费视为重新启用
    """
    card = db.session.get(MembershipCard, card_id)
    if card is None:
        raise CardError("card_not_found", status_code=404)
    if card.status == CardStatus.CANCELLED:
        raise CardError("card_cancelled")
    if card.status == CardStatus.FROZEN:
        raise CardError("card_frozen")

    ct = card.card_type
    if ct.duration_days is not None:
        base = card.end_date if card.end_date and card.end_date > _today() else _today()
        card.end_date = base + timedelta(days=ct.duration_days)
    if ct.total_visits is not None:
        card.remaining_visits = (card.remaining_visits or 0) + ct.total_visits

    if card.status == CardStatus.EXPIRED:
        card.status = CardStatus.ACTIVE
    db.session.commit()
    return card


def freeze_card(card_id: int) -> MembershipCard:
    card = db.session.get(MembershipCard, card_id)
    if card is None:
        raise CardError("card_not_found", status_code=404)
    if card.status != CardStatus.ACTIVE:
        raise CardError("card_not_active")
    card.status = CardStatus.FROZEN
    card.frozen_at = _utcnow()
    db.session.commit()
    return card


def unfreeze_card(card_id: int) -> MembershipCard:
    card = db.session.get(MembershipCard, card_id)
    if card is None:
        raise CardError("card_not_found", status_code=404)
    if card.status != CardStatus.FROZEN:
        raise CardError("card_not_frozen")
    # 已过期 → 解冻后仍按过期处理
    if card.end_date is not None and card.end_date < _today():
        card.status = CardStatus.EXPIRED
    else:
        card.status = CardStatus.ACTIVE
    card.frozen_at = None
    db.session.commit()
    return card


def cancel_card(card_id: int) -> MembershipCard:
    card = db.session.get(MembershipCard, card_id)
    if card is None:
        raise CardError("card_not_found", status_code=404)
    if card.status == CardStatus.CANCELLED:
        raise CardError("card_cancelled")
    card.status = CardStatus.CANCELLED
    db.session.commit()
    return card


def sweep_expired() -> int:
    """把已到期但仍标 active 的卡批量置 expired。返回受影响行数。

    本设计走 service 而不是 DB trigger：实现简单、易测试，且可以由 CLI / 定时任务调用。
    """
    today = _today()
    stmt = select(MembershipCard).where(
        MembershipCard.status == CardStatus.ACTIVE,
        MembershipCard.end_date.is_not(None),
        MembershipCard.end_date < today,
    )
    cards = db.session.execute(stmt).scalars().all()
    for c in cards:
        c.status = CardStatus.EXPIRED
    if cards:
        db.session.commit()
    return len(cards)
