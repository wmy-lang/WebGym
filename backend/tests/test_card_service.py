"""card_service 单测 —— 直接调 service，不走 HTTP。"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.extensions import db
from app.models import CardStatus, MembershipCard, User, UserRole
from app.services import card_service
from app.services.card_service import CardError, IssueInput


def _alice_id() -> int:
    return db.session.query(User).filter_by(username="alice").one().id


def _admin_id() -> int:
    return db.session.query(User).filter_by(username="admin").one().id


# ---------- issue ----------

def test_issue_year_card(app, seeded_users, card_types):
    with app.app_context():
        card = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["year"], issued_by_id=_admin_id())
        )
        assert card.status == CardStatus.ACTIVE
        assert card.end_date == date.today() + timedelta(days=365)
        assert card.remaining_visits is None
        assert card.card_no.startswith("C")
        assert card.issued_by == _admin_id()


def test_issue_visit_card_sets_remaining(app, seeded_users, card_types):
    with app.app_context():
        card = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["visit"])
        )
        assert card.end_date is None
        assert card.remaining_visits == 10


def test_issue_for_non_member_fails(app, seeded_users, card_types):
    with app.app_context():
        with pytest.raises(CardError) as exc:
            card_service.issue_card(
                IssueInput(member_id=_admin_id(), card_type_id=card_types["year"])
            )
        assert exc.value.code == "member_not_found"


def test_issue_for_disabled_member_fails(app, seeded_users, card_types):
    with app.app_context():
        u = db.session.get(User, _alice_id())
        u.is_active = False
        db.session.commit()

        with pytest.raises(CardError) as exc:
            card_service.issue_card(
                IssueInput(member_id=_alice_id(), card_type_id=card_types["year"])
            )
        assert exc.value.code == "member_disabled"


def test_issue_inactive_card_type_fails(app, seeded_users, card_types):
    from app.models import CardType

    with app.app_context():
        ct = db.session.get(CardType, card_types["year"])
        ct.is_active = False
        db.session.commit()

        with pytest.raises(CardError) as exc:
            card_service.issue_card(
                IssueInput(member_id=_alice_id(), card_type_id=card_types["year"])
            )
        assert exc.value.code == "card_type_not_found"


def test_card_no_sequence_increments(app, seeded_users, card_types):
    with app.app_context():
        a = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["year"])
        )
        b = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["visit"])
        )
        assert int(b.card_no[-6:]) == int(a.card_no[-6:]) + 1


# ---------- renew ----------

def test_renew_extends_end_date(app, seeded_users, card_types):
    with app.app_context():
        card = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["year"])
        )
        original_end = card.end_date

        card = card_service.renew_card(card.id)
        assert card.end_date == original_end + timedelta(days=365)


def test_renew_adds_visits(app, seeded_users, card_types):
    with app.app_context():
        card = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["visit"])
        )
        card.remaining_visits = 3
        db.session.commit()

        card = card_service.renew_card(card.id)
        assert card.remaining_visits == 13


def test_renew_expired_reactivates(app, seeded_users, card_types):
    with app.app_context():
        card = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["year"])
        )
        card.status = CardStatus.EXPIRED
        card.end_date = date.today() - timedelta(days=10)
        db.session.commit()

        card = card_service.renew_card(card.id)
        assert card.status == CardStatus.ACTIVE
        # 基线应该是今天，不是已过去的 end_date
        assert card.end_date == date.today() + timedelta(days=365)


def test_renew_frozen_blocked(app, seeded_users, card_types):
    with app.app_context():
        card = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["year"])
        )
        card_service.freeze_card(card.id)

        with pytest.raises(CardError) as exc:
            card_service.renew_card(card.id)
        assert exc.value.code == "card_frozen"


def test_renew_cancelled_blocked(app, seeded_users, card_types):
    with app.app_context():
        card = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["year"])
        )
        card_service.cancel_card(card.id)

        with pytest.raises(CardError) as exc:
            card_service.renew_card(card.id)
        assert exc.value.code == "card_cancelled"


# ---------- freeze / unfreeze ----------

def test_freeze_active_card(app, seeded_users, card_types):
    with app.app_context():
        card = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["year"])
        )
        card = card_service.freeze_card(card.id)
        assert card.status == CardStatus.FROZEN
        assert card.frozen_at is not None


def test_freeze_non_active_fails(app, seeded_users, card_types):
    with app.app_context():
        card = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["year"])
        )
        card_service.freeze_card(card.id)
        with pytest.raises(CardError) as exc:
            card_service.freeze_card(card.id)
        assert exc.value.code == "card_not_active"


def test_unfreeze_returns_active(app, seeded_users, card_types):
    with app.app_context():
        card = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["year"])
        )
        card_service.freeze_card(card.id)
        card = card_service.unfreeze_card(card.id)
        assert card.status == CardStatus.ACTIVE
        assert card.frozen_at is None


def test_unfreeze_already_expired_card_marks_expired(app, seeded_users, card_types):
    with app.app_context():
        card = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["year"])
        )
        card_service.freeze_card(card.id)
        # 把 end_date 推到过去
        c = db.session.get(MembershipCard, card.id)
        c.end_date = date.today() - timedelta(days=1)
        db.session.commit()

        c = card_service.unfreeze_card(card.id)
        assert c.status == CardStatus.EXPIRED


# ---------- cancel / sweep ----------

def test_cancel_terminates(app, seeded_users, card_types):
    with app.app_context():
        card = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["year"])
        )
        card = card_service.cancel_card(card.id)
        assert card.status == CardStatus.CANCELLED


def test_sweep_expired_marks_expired_cards(app, seeded_users, card_types):
    with app.app_context():
        a = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["year"])
        )
        b = card_service.issue_card(
            IssueInput(member_id=_alice_id(), card_type_id=card_types["visit"])
        )
        # a 已过期，b 是次卡（end_date 为空，不该被扫到）
        db.session.get(MembershipCard, a.id).end_date = date.today() - timedelta(days=1)
        db.session.commit()

        affected = card_service.sweep_expired()
        assert affected == 1
        assert db.session.get(MembershipCard, a.id).status == CardStatus.EXPIRED
        assert db.session.get(MembershipCard, b.id).status == CardStatus.ACTIVE
