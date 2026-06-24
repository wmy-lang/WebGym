"""``/api/cards/*`` API 测试。"""
from __future__ import annotations

import pytest


@pytest.fixture
def staff_client(client, seeded_users, card_types, do_login):
    do_login("staff01", "staff123")
    return client


@pytest.fixture
def member_client(client, seeded_users, card_types, do_login):
    do_login("alice", "member123")
    return client


def _alice_id(app):
    from app.extensions import db
    from app.models import User

    with app.app_context():
        return db.session.query(User).filter_by(username="alice").one().id


# ---------- issue ----------

def test_issue_requires_staff(client, seeded_users, card_types, app):
    aid = _alice_id(app)
    resp = client.post("/api/cards", json={"member_id": aid, "card_type_id": card_types["year"]})
    assert resp.status_code == 401


def test_member_cannot_issue(member_client, app, card_types):
    aid = _alice_id(app)
    resp = member_client.post(
        "/api/cards", json={"member_id": aid, "card_type_id": card_types["year"]}
    )
    assert resp.status_code == 403


def test_issue_card_happy_path(staff_client, app, card_types):
    aid = _alice_id(app)
    resp = staff_client.post(
        "/api/cards", json={"member_id": aid, "card_type_id": card_types["year"]}
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["status"] == "active"
    assert body["card_type_name"] == "年卡"
    assert body["member_name"] == "张爱丽"


def test_issue_card_validation_error(staff_client):
    resp = staff_client.post("/api/cards", json={})
    assert resp.status_code == 400


def test_issue_card_unknown_member(staff_client, card_types):
    resp = staff_client.post(
        "/api/cards", json={"member_id": 9999, "card_type_id": card_types["year"]}
    )
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "member_not_found"


# ---------- list / retrieve / role-based scoping ----------

def test_list_cards_member_sees_only_own(client, seeded_users, card_types, do_login, app):
    aid = _alice_id(app)
    # staff 先给 alice 办一张
    do_login("staff01", "staff123")
    client.post("/api/cards", json={"member_id": aid, "card_type_id": card_types["year"]})
    client.post("/api/auth/logout")

    # 切到 alice 看自己
    do_login("alice", "member123")
    listing = client.get("/api/cards").get_json()
    assert listing["meta"]["total"] == 1


def test_retrieve_other_member_card_forbidden(client, seeded_users, card_types, do_login, app):
    aid = _alice_id(app)
    # staff 给 alice 办一张 + 建 bob
    do_login("staff01", "staff123")
    created = client.post(
        "/api/cards", json={"member_id": aid, "card_type_id": card_types["year"]}
    ).get_json()
    client.post(
        "/api/members",
        json={
            "username": "bob",
            "password": "bob12345",
            "real_name": "鲍博",
            "phone": "13800000099",
        },
    )
    client.post("/api/auth/logout")

    # bob 登录，去查 alice 的卡 → 403
    do_login("bob", "bob12345")
    resp = client.get(f"/api/cards/{created['id']}")
    assert resp.status_code == 403


def test_filter_by_member_id_staff(staff_client, app, card_types):
    aid = _alice_id(app)
    staff_client.post(
        "/api/cards", json={"member_id": aid, "card_type_id": card_types["year"]}
    )
    resp = staff_client.get(f"/api/cards?member_id={aid}")
    assert resp.status_code == 200
    assert resp.get_json()["meta"]["total"] == 1


def test_filter_invalid_status(staff_client):
    resp = staff_client.get("/api/cards?status=banana")
    assert resp.status_code == 400


# ---------- actions ----------

def _issue(staff_client, app, card_types, key="year"):
    aid = _alice_id(app)
    return staff_client.post(
        "/api/cards", json={"member_id": aid, "card_type_id": card_types[key]}
    ).get_json()


def test_freeze_then_unfreeze(staff_client, app, card_types):
    card = _issue(staff_client, app, card_types)

    resp = staff_client.post(f"/api/cards/{card['id']}/freeze")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "frozen"

    resp = staff_client.post(f"/api/cards/{card['id']}/unfreeze")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "active"


def test_renew_extends_end_date(staff_client, app, card_types):
    card = _issue(staff_client, app, card_types)
    original_end = card["end_date"]

    resp = staff_client.post(f"/api/cards/{card['id']}/renew")
    assert resp.status_code == 200
    assert resp.get_json()["end_date"] > original_end


def test_cancel_terminates(staff_client, app, card_types):
    card = _issue(staff_client, app, card_types)
    resp = staff_client.post(f"/api/cards/{card['id']}/cancel")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "cancelled"


def test_freeze_already_frozen_400(staff_client, app, card_types):
    card = _issue(staff_client, app, card_types)
    staff_client.post(f"/api/cards/{card['id']}/freeze")
    resp = staff_client.post(f"/api/cards/{card['id']}/freeze")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "card_not_active"


def test_action_card_not_found(staff_client):
    resp = staff_client.post("/api/cards/9999/renew")
    assert resp.status_code == 404


def test_sweep_expired_endpoint(staff_client, app, card_types):
    from datetime import date, timedelta

    from app.extensions import db
    from app.models import MembershipCard

    card = _issue(staff_client, app, card_types)
    with app.app_context():
        c = db.session.get(MembershipCard, card["id"])
        c.end_date = date.today() - timedelta(days=1)
        db.session.commit()

    resp = staff_client.post("/api/cards/sweep-expired")
    assert resp.status_code == 200
    assert resp.get_json()["affected"] == 1
