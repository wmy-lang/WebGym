"""booking_service 单测 —— 直接调 service，不走 HTTP。"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from app.extensions import db
from app.models import (
    BookingSource,
    BookingStatus,
    CardStatus,
    ClassSession,
    MembershipCard,
    User,
    UserRole,
)
from app.services import booking_service
from app.services.booking_service import BookingError, BookingInput


def _alice_id() -> int:
    return db.session.query(User).filter_by(username="alice").one().id


def _admin_id() -> int:
    return db.session.query(User).filter_by(username="admin").one().id


# ---------- book_session ----------

def test_book_happy_path(app, alice_year_card, future_session):
    with app.app_context():
        b = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        assert b.status == BookingStatus.BOOKED
        assert b.card_id == alice_year_card


def test_book_no_card(app, seeded_users, future_session):
    with app.app_context():
        with pytest.raises(BookingError) as exc:
            booking_service.book_session(
                BookingInput(member_id=_alice_id(), session_id=future_session)
            )
        assert exc.value.code == "no_usable_card"


def test_book_disabled_member(app, alice_year_card, future_session):
    with app.app_context():
        u = db.session.get(User, _alice_id())
        u.is_active = False
        db.session.commit()
        with pytest.raises(BookingError) as exc:
            booking_service.book_session(
                BookingInput(member_id=_alice_id(), session_id=future_session)
            )
        assert exc.value.code == "member_disabled"


def test_book_unknown_session(app, alice_year_card):
    with app.app_context():
        with pytest.raises(BookingError) as exc:
            booking_service.book_session(
                BookingInput(member_id=_alice_id(), session_id=9999)
            )
        assert exc.value.code == "session_not_found"


def test_book_session_in_past(app, alice_year_card, class_def):
    """session 已经开始 → 不能预约。"""
    with app.app_context():
        past_start = datetime.utcnow() - timedelta(hours=1)
        s = ClassSession(
            class_def_id=class_def,
            start_at=past_start,
            end_at=past_start + timedelta(hours=1),
            capacity=5,
        )
        db.session.add(s)
        db.session.commit()
        with pytest.raises(BookingError) as exc:
            booking_service.book_session(
                BookingInput(member_id=_alice_id(), session_id=s.id)
            )
        assert exc.value.code == "session_already_started"


def test_book_duplicate(app, alice_year_card, future_session):
    with app.app_context():
        booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        with pytest.raises(BookingError) as exc:
            booking_service.book_session(
                BookingInput(member_id=_alice_id(), session_id=future_session)
            )
        assert exc.value.code == "already_booked"


def test_book_can_rebook_after_cancel(app, alice_year_card, future_session):
    """取消后允许再预约（partial unique index 的核心约束）。"""
    with app.app_context():
        b = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        booking_service.cancel_booking(
            b.id, actor_id=_admin_id(), actor_role=UserRole.ADMIN
        )
        b2 = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        assert b2.id != b.id
        assert b2.status == BookingStatus.BOOKED


def test_book_session_full(app, alice_year_card, future_session, card_types):
    """容量 = 2：先建 bob/carol 各办卡占满，再让 alice 预约失败。"""
    from app.models import MembershipCard

    with app.app_context():
        # 把 future_session 容量限定到 2（fixture 默认就是 2）；占 2 个
        for username, phone in [("bob", "13800000010"), ("carol", "13800000011")]:
            u = User(username=username, role=UserRole.MEMBER)
            u.set_password("pw123456")
            from app.models import MemberProfile

            u.profile = MemberProfile(real_name=username, phone=phone)
            db.session.add(u)
            db.session.flush()
            db.session.add(
                MembershipCard(
                    card_no=f"C-{username}",
                    member_id=u.id,
                    card_type_id=card_types["year"],
                    start_date=date.today(),
                    end_date=date.today() + timedelta(days=365),
                    status=CardStatus.ACTIVE,
                )
            )
            db.session.commit()
            booking_service.book_session(
                BookingInput(member_id=u.id, session_id=future_session)
            )

        with pytest.raises(BookingError) as exc:
            booking_service.book_session(
                BookingInput(member_id=_alice_id(), session_id=future_session)
            )
        assert exc.value.code == "session_full"


def test_book_picks_visit_card_when_only_one(app, seeded_users, card_types, future_session):
    """只有次卡可用 → 应能预约。"""
    with app.app_context():
        db.session.add(
            MembershipCard(
                card_no="V-1",
                member_id=_alice_id(),
                card_type_id=card_types["visit"],
                start_date=date.today(),
                remaining_visits=3,
                status=CardStatus.ACTIVE,
            )
        )
        db.session.commit()
        b = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        card = db.session.get(MembershipCard, b.card_id)
        assert card.remaining_visits == 3  # 预约阶段不扣


def test_book_skips_frozen_card(app, seeded_users, card_types, future_session):
    """frozen 卡不应被挑中；如果没别的可用卡 → no_usable_card。"""
    with app.app_context():
        db.session.add(
            MembershipCard(
                card_no="F-1",
                member_id=_alice_id(),
                card_type_id=card_types["year"],
                start_date=date.today(),
                end_date=date.today() + timedelta(days=365),
                status=CardStatus.FROZEN,
            )
        )
        db.session.commit()
        with pytest.raises(BookingError) as exc:
            booking_service.book_session(
                BookingInput(member_id=_alice_id(), session_id=future_session)
            )
        assert exc.value.code == "no_usable_card"


# ---------- cancel ----------

def test_cancel_self_ok(app, alice_year_card, future_session):
    with app.app_context():
        b = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        b = booking_service.cancel_booking(
            b.id, actor_id=_alice_id(), actor_role=UserRole.MEMBER
        )
        assert b.status == BookingStatus.CANCELLED
        assert b.cancelled_at is not None


def test_cancel_cutoff_blocks_member(app, alice_year_card, class_def):
    """开课前 1 小时（< 2h 截止）会员不能自助取消，admin 可以。"""
    from app.models import ClassSession

    with app.app_context():
        start = datetime.utcnow() + timedelta(minutes=30)
        s = ClassSession(
            class_def_id=class_def,
            start_at=start,
            end_at=start + timedelta(hours=1),
            capacity=5,
        )
        db.session.add(s)
        db.session.commit()

        b = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=s.id)
        )

        with pytest.raises(BookingError) as exc:
            booking_service.cancel_booking(
                b.id, actor_id=_alice_id(), actor_role=UserRole.MEMBER
            )
        assert exc.value.code == "cancel_cutoff_passed"

        # admin 应能取消
        b = booking_service.cancel_booking(
            b.id, actor_id=_admin_id(), actor_role=UserRole.ADMIN
        )
        assert b.status == BookingStatus.CANCELLED


def test_cancel_other_members_booking_forbidden(app, alice_year_card, future_session):
    with app.app_context():
        b = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        # 用一个非真实 member 的 id 即可走 member 分支
        with pytest.raises(BookingError) as exc:
            booking_service.cancel_booking(
                b.id, actor_id=99999, actor_role=UserRole.MEMBER
            )
        assert exc.value.code == "forbidden"


def test_cancel_cancelled_is_idempotent(app, alice_year_card, future_session):
    with app.app_context():
        b = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        booking_service.cancel_booking(
            b.id, actor_id=_admin_id(), actor_role=UserRole.ADMIN
        )
        # 再调一次仍然返回 cancelled，不抛错
        b2 = booking_service.cancel_booking(
            b.id, actor_id=_admin_id(), actor_role=UserRole.ADMIN
        )
        assert b2.status == BookingStatus.CANCELLED


def test_cancel_attended_locked(app, alice_year_card, future_session):
    with app.app_context():
        b = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        booking_service.check_in(
            b.id, operator_id=_admin_id(), operator_role=UserRole.ADMIN
        )
        with pytest.raises(BookingError) as exc:
            booking_service.cancel_booking(
                b.id, actor_id=_admin_id(), actor_role=UserRole.ADMIN
            )
        assert exc.value.code == "booking_locked"


# ---------- check_in ----------

def test_check_in_happy_path(app, alice_year_card, future_session):
    with app.app_context():
        b = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        att = booking_service.check_in(
            b.id, operator_id=_admin_id(), operator_role=UserRole.ADMIN
        )
        assert att.booking_id == b.id
        b2 = db.session.get(type(b), b.id)
        assert b2.status == BookingStatus.ATTENDED


def test_check_in_member_self_ok(app, alice_year_card, future_session):
    with app.app_context():
        b = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        booking_service.check_in(
            b.id, operator_id=_alice_id(), operator_role=UserRole.MEMBER
        )


def test_check_in_other_member_forbidden(app, alice_year_card, future_session):
    with app.app_context():
        b = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        with pytest.raises(BookingError) as exc:
            booking_service.check_in(
                b.id, operator_id=99999, operator_role=UserRole.MEMBER
            )
        assert exc.value.code == "forbidden"


def test_check_in_decrements_visit_card(app, seeded_users, card_types, future_session):
    with app.app_context():
        db.session.add(
            MembershipCard(
                card_no="V-2",
                member_id=_alice_id(),
                card_type_id=card_types["visit"],
                start_date=date.today(),
                remaining_visits=3,
                status=CardStatus.ACTIVE,
            )
        )
        db.session.commit()
        b = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        booking_service.check_in(
            b.id, operator_id=_admin_id(), operator_role=UserRole.ADMIN
        )
        card = db.session.get(MembershipCard, b.card_id)
        assert card.remaining_visits == 2


def test_check_in_duplicate_blocked(app, alice_year_card, future_session):
    with app.app_context():
        b = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        booking_service.check_in(
            b.id, operator_id=_admin_id(), operator_role=UserRole.ADMIN
        )
        with pytest.raises(BookingError) as exc:
            booking_service.check_in(
                b.id, operator_id=_admin_id(), operator_role=UserRole.ADMIN
            )
        assert exc.value.code == "already_checked_in"


def test_check_in_cancelled_booking_blocked(app, alice_year_card, future_session):
    with app.app_context():
        b = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        booking_service.cancel_booking(
            b.id, actor_id=_admin_id(), actor_role=UserRole.ADMIN
        )
        with pytest.raises(BookingError) as exc:
            booking_service.check_in(
                b.id, operator_id=_admin_id(), operator_role=UserRole.ADMIN
            )
        assert exc.value.code == "booking_not_active"


def test_check_in_for_cancelled_session_blocked(app, alice_year_card, future_session):
    """session 被 cancel 后，预约会被同步取消 → booking_not_active。"""
    from app.models import SessionStatus

    with app.app_context():
        b = booking_service.book_session(
            BookingInput(member_id=_alice_id(), session_id=future_session)
        )
        s = db.session.get(ClassSession, future_session)
        s.status = SessionStatus.CANCELLED
        db.session.commit()
        with pytest.raises(BookingError) as exc:
            booking_service.check_in(
                b.id, operator_id=_admin_id(), operator_role=UserRole.ADMIN
            )
        # booking 仍是 booked，但 session 不再 scheduled
        assert exc.value.code == "session_not_open"
