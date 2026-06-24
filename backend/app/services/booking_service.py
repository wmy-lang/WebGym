"""预约 / 取消 / 签到 业务规则。对照 Spring `@Service` + ``@Transactional``。

设计要点：
- **挑卡策略**：预约时按"end_date 最近优先 + 期限卡优先 + ID 升序"挑一张可用卡；
  签到时再扣（次卡）；预约阶段不锁次数，避免"反复预约 / 取消"刷次数。
- **时间策略**：所有"未来 / 截止"判定都用 ``datetime.utcnow()``，与 DB 中存的
  naive UTC 时间一致（ClassSession.start_at 写入时不带 tzinfo）。
- **2 小时截止**：会员自助取消必须距开课 > 2 小时；admin 始终可取消。
- **容量校验**：在 service 内 SELECT COUNT 后再 INSERT，结合
  ``uq_bookings_member_session_active`` 部分唯一索引兜底"同人重复预约"。
- **状态机**：booked → cancelled / attended / no_show。attended / no_show
  之后不可再变；cancelled 不可复活（再次预约会生成新 Booking 行）。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..extensions import db
from ..models import (
    Attendance,
    Booking,
    BookingSource,
    BookingStatus,
    CardStatus,
    ClassSession,
    MembershipCard,
    SessionStatus,
    User,
    UserRole,
)

CANCEL_CUTOFF = timedelta(hours=2)


class BookingError(Exception):
    def __init__(self, code: str, status_code: int = 400):
        super().__init__(code)
        self.code = code
        self.status_code = status_code


@dataclass
class BookingInput:
    member_id: int
    session_id: int
    source: BookingSource = BookingSource.SELF


def _utcnow() -> datetime:
    return datetime.utcnow()


def _assert_member(member_id: int) -> User:
    user = db.session.get(User, member_id)
    if user is None or user.role != UserRole.MEMBER:
        raise BookingError("member_not_found", 404)
    if not user.is_active:
        raise BookingError("member_disabled", 403)
    return user


def _assert_session_open(session_id: int) -> ClassSession:
    s = db.session.get(ClassSession, session_id)
    if s is None:
        raise BookingError("session_not_found", 404)
    if s.status != SessionStatus.SCHEDULED:
        raise BookingError("session_not_open")
    if s.start_at <= _utcnow():
        raise BookingError("session_already_started")
    return s


def _pick_usable_card(member_id: int, when: datetime) -> MembershipCard | None:
    """挑一张当下可用的卡。

    优先级：1) end_date 最近的；2) 期限卡优先（end_date IS NOT NULL）；3) id 升序。
    次卡 ``remaining_visits = 0`` 视为不可用（``is_usable_on`` 已判定）。
    """
    today = when.date()
    stmt = (
        select(MembershipCard)
        .where(
            MembershipCard.member_id == member_id,
            MembershipCard.status == CardStatus.ACTIVE,
        )
        .order_by(
            # 期限卡 end_date 升序排前；NULL（次卡）排后
            MembershipCard.end_date.is_(None).asc(),
            MembershipCard.end_date.asc(),
            MembershipCard.id.asc(),
        )
    )
    for card in db.session.execute(stmt).scalars():
        if card.is_usable_on(today):
            return card
    return None


def _booked_count(session_id: int) -> int:
    return db.session.scalar(
        select(func.count(Booking.id))
        .where(Booking.session_id == session_id)
        .where(Booking.status != BookingStatus.CANCELLED)
    ) or 0


def book_session(data: BookingInput) -> Booking:
    """会员预约一节课。"""
    _assert_member(data.member_id)
    s = _assert_session_open(data.session_id)

    card = _pick_usable_card(data.member_id, _utcnow())
    if card is None:
        raise BookingError("no_usable_card", 403)

    # 重复预约：partial unique 索引兜底，但先查一遍便于返回干净错误
    existing = db.session.scalar(
        select(Booking)
        .where(Booking.member_id == data.member_id)
        .where(Booking.session_id == data.session_id)
        .where(Booking.status != BookingStatus.CANCELLED)
    )
    if existing is not None:
        raise BookingError("already_booked", 409)

    if _booked_count(s.id) >= s.capacity:
        raise BookingError("session_full", 409)

    b = Booking(
        member_id=data.member_id,
        session_id=s.id,
        card_id=card.id,
        status=BookingStatus.BOOKED,
        booked_at=_utcnow(),
        source=data.source,
    )
    db.session.add(b)
    try:
        db.session.commit()
    except IntegrityError:
        # 兜底：同一秒两请求竞态命中部分唯一索引
        db.session.rollback()
        raise BookingError("already_booked", 409) from None
    return b


def cancel_booking(
    booking_id: int, *, actor_id: int, actor_role: UserRole
) -> Booking:
    """取消预约。

    - 会员只能取消自己的；
    - 会员距开课 ≤ 2h 不能取消；admin/staff 可绕过；
    - 已 attended / no_show 不能取消（已结算）；
    - cancelled 幂等：直接返回。
    """
    b = db.session.get(Booking, booking_id)
    if b is None:
        raise BookingError("booking_not_found", 404)

    if actor_role == UserRole.MEMBER and b.member_id != actor_id:
        raise BookingError("forbidden", 403)

    if b.status == BookingStatus.CANCELLED:
        return b
    if b.status in (BookingStatus.ATTENDED, BookingStatus.NO_SHOW):
        raise BookingError("booking_locked")

    if actor_role == UserRole.MEMBER:
        if b.session.start_at - _utcnow() <= CANCEL_CUTOFF:
            raise BookingError("cancel_cutoff_passed")

    b.status = BookingStatus.CANCELLED
    b.cancelled_at = _utcnow()
    db.session.commit()
    return b


def check_in(
    booking_id: int, *, operator_id: int, operator_role: UserRole
) -> Attendance:
    """签到。

    规则：
    - 仅 ``booked`` 状态可签到；
    - 会员只能为自己签到；
    - session 已 cancelled / finished 不能签到；
    - 次卡在此处扣 1 次；
    - 重复签到 → 409。
    """
    b = db.session.get(Booking, booking_id)
    if b is None:
        raise BookingError("booking_not_found", 404)
    if operator_role == UserRole.MEMBER and b.member_id != operator_id:
        raise BookingError("forbidden", 403)
    if b.attendance is not None:
        raise BookingError("already_checked_in", 409)
    if b.status != BookingStatus.BOOKED:
        raise BookingError("booking_not_active")

    s: ClassSession = b.session
    if s.status != SessionStatus.SCHEDULED:
        raise BookingError("session_not_open")

    # 次卡：扣 1 次（其它卡不动）
    card = b.card
    if card is not None and card.remaining_visits is not None:
        if card.remaining_visits <= 0:
            raise BookingError("card_visits_exhausted")
        card.remaining_visits -= 1

    b.status = BookingStatus.ATTENDED
    att = Attendance(
        booking_id=b.id,
        checked_in_at=_utcnow(),
        checked_in_by=operator_id,
    )
    db.session.add(att)
    db.session.commit()
    return att
