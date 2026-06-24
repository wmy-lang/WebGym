"""模型层基础单测：建表、关系、唯一约束、状态机辅助方法。"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    Booking,
    BookingStatus,
    CardStatus,
    CardType,
    ClassDefinition,
    ClassSession,
    Coach,
    Gender,
    MemberProfile,
    MembershipCard,
    SessionStatus,
    User,
    UserRole,
)


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def _make_member(username="alice", phone="13800000001") -> User:
    u = User(username=username, role=UserRole.MEMBER)
    u.set_password("pw")
    u.profile = MemberProfile(real_name="Alice", phone=phone, gender=Gender.FEMALE)
    db.session.add(u)
    db.session.flush()
    return u


def test_user_password_hash_and_role(app_ctx):
    u = User(username="admin", role=UserRole.ADMIN)
    u.set_password("secret")
    db.session.add(u)
    db.session.commit()

    fetched = db.session.query(User).filter_by(username="admin").one()
    assert fetched.check_password("secret")
    assert not fetched.check_password("wrong")
    assert fetched.is_admin and fetched.is_staff
    assert fetched.password_hash != "secret"


def test_member_profile_cascade_delete(app_ctx):
    u = _make_member()
    db.session.commit()
    assert db.session.query(MemberProfile).count() == 1
    db.session.delete(u)
    db.session.commit()
    assert db.session.query(MemberProfile).count() == 0


def test_phone_unique(app_ctx):
    _make_member("alice", "13800000001")
    db.session.commit()
    with pytest.raises(IntegrityError):
        _make_member("bob", "13800000001")
        db.session.commit()


def test_card_usability_status_machine(app_ctx):
    member = _make_member()
    ct = CardType(name="年卡", duration_days=365, price=Decimal("1999.00"))
    db.session.add(ct)
    db.session.flush()

    today = date.today()
    card = MembershipCard(
        card_no="C0001",
        member_id=member.id,
        card_type_id=ct.id,
        start_date=today,
        end_date=today + timedelta(days=365),
        status=CardStatus.ACTIVE,
    )
    db.session.add(card)
    db.session.commit()

    assert card.is_usable_on(today)

    card.status = CardStatus.FROZEN
    assert not card.is_usable_on(today)

    card.status = CardStatus.ACTIVE
    card.end_date = today - timedelta(days=1)
    assert not card.is_usable_on(today)


def test_visit_card_remaining_visits_blocks_usage(app_ctx):
    member = _make_member()
    ct = CardType(name="10 次卡", total_visits=10, price=Decimal("499.00"))
    db.session.add(ct)
    db.session.flush()

    card = MembershipCard(
        card_no="V0001",
        member_id=member.id,
        card_type_id=ct.id,
        start_date=date.today(),
        remaining_visits=0,
    )
    db.session.add(card)
    db.session.commit()
    assert not card.is_usable_on(date.today())


def test_booking_partial_unique_allows_recreate_after_cancel(app_ctx):
    """同会员同 session：第一条 booked 后再发 booked 应当冲突；
    把第一条改成 cancelled，则可以重新预约。"""
    member = _make_member()
    coach = Coach(name="李教练")
    db.session.add(coach)
    db.session.flush()

    cd = ClassDefinition(name="瑜伽", coach_id=coach.id, capacity=10, duration_minutes=60)
    db.session.add(cd)
    db.session.flush()

    start = datetime.now(timezone.utc) + timedelta(days=1)
    sess = ClassSession(
        class_def_id=cd.id,
        coach_id=coach.id,
        start_at=start,
        end_at=start + timedelta(hours=1),
        capacity=10,
        status=SessionStatus.SCHEDULED,
    )
    db.session.add(sess)
    db.session.flush()

    b1 = Booking(member_id=member.id, session_id=sess.id, status=BookingStatus.BOOKED)
    db.session.add(b1)
    db.session.commit()

    # 第二条 booked 触发部分唯一索引冲突
    db.session.add(Booking(member_id=member.id, session_id=sess.id, status=BookingStatus.BOOKED))
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()

    # 把第一条取消，再加新的 booked 应可成功
    b1.status = BookingStatus.CANCELLED
    b1.cancelled_at = datetime.now(timezone.utc)
    db.session.commit()

    db.session.add(Booking(member_id=member.id, session_id=sess.id, status=BookingStatus.BOOKED))
    db.session.commit()
    assert db.session.query(Booking).count() == 2


def test_all_tables_created(app_ctx):
    """metadata 完整性：9 张表都建出来。"""
    expected = {
        "users",
        "member_profiles",
        "coaches",
        "card_types",
        "membership_cards",
        "class_definitions",
        "class_sessions",
        "bookings",
        "attendances",
    }
    assert expected.issubset(set(db.metadata.tables.keys()))
