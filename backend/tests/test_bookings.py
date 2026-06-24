"""``/api/bookings/*`` API 测试。"""
from __future__ import annotations

import pytest


@pytest.fixture
def alice_logged_in(client, alice_year_card, future_session, do_login):
    do_login("alice", "member123")
    return client


@pytest.fixture
def staff_logged_in(client, seeded_users, future_session, do_login):
    do_login("staff01", "staff123")
    return client


def _alice_id(app):
    from app.extensions import db
    from app.models import User

    with app.app_context():
        return db.session.query(User).filter_by(username="alice").one().id


# ---------- create ----------

def test_member_books_self(alice_logged_in, future_session):
    resp = alice_logged_in.post("/api/bookings", json={"session_id": future_session})
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["status"] == "booked"
    assert body["source"] == "self"
    assert body["class_name"] == "瑜伽入门"


def test_anonymous_cannot_book(client, future_session):
    resp = client.post("/api/bookings", json={"session_id": future_session})
    assert resp.status_code == 401


def test_member_cannot_specify_other_member_id(alice_logged_in, future_session, app):
    # 用 admin 的 id 假冒下单 → 403
    from app.extensions import db
    from app.models import User

    with app.app_context():
        admin_id = db.session.query(User).filter_by(username="admin").one().id
    resp = alice_logged_in.post(
        "/api/bookings", json={"session_id": future_session, "member_id": admin_id}
    )
    assert resp.status_code == 403


def test_staff_must_specify_member_id(staff_logged_in, future_session):
    resp = staff_logged_in.post("/api/bookings", json={"session_id": future_session})
    assert resp.status_code == 400


def test_staff_admin_creates_for_member(staff_logged_in, future_session, app, alice_year_card):
    aid = _alice_id(app)
    resp = staff_logged_in.post(
        "/api/bookings", json={"session_id": future_session, "member_id": aid}
    )
    assert resp.status_code == 201, resp.get_json()
    assert resp.get_json()["source"] == "admin"


def test_book_no_card(staff_logged_in, future_session, app):
    """没办过卡，预约应失败。"""
    aid = _alice_id(app)
    resp = staff_logged_in.post(
        "/api/bookings", json={"session_id": future_session, "member_id": aid}
    )
    assert resp.status_code == 403
    assert resp.get_json()["error"] == "no_usable_card"


def test_book_validation_error(alice_logged_in):
    resp = alice_logged_in.post("/api/bookings", json={})
    assert resp.status_code == 400


def test_book_duplicate(alice_logged_in, future_session):
    alice_logged_in.post("/api/bookings", json={"session_id": future_session})
    resp = alice_logged_in.post("/api/bookings", json={"session_id": future_session})
    assert resp.status_code == 409


# ---------- list / retrieve ----------

def test_member_list_self_only(alice_logged_in, future_session):
    alice_logged_in.post("/api/bookings", json={"session_id": future_session})
    body = alice_logged_in.get("/api/bookings").get_json()
    assert body["meta"]["total"] == 1


def test_member_cannot_view_other_booking(client, alice_year_card, future_session, do_login, app):
    # 1) staff 代 alice 下单
    do_login("staff01", "staff123")
    created = client.post(
        "/api/bookings",
        json={"session_id": future_session, "member_id": _alice_id(app)},
    ).get_json()
    client.post("/api/auth/logout")

    # 2) 建 bob 并登录，去看 alice 的预约
    do_login("admin", "admin123")
    client.post(
        "/api/members",
        json={
            "username": "bob",
            "password": "bob12345",
            "real_name": "鲍博",
            "phone": "13800000077",
        },
    )
    client.post("/api/auth/logout")

    do_login("bob", "bob12345")
    resp = client.get(f"/api/bookings/{created['id']}")
    assert resp.status_code == 403


def test_staff_filter_by_member(staff_logged_in, future_session, app, alice_year_card):
    aid = _alice_id(app)
    staff_logged_in.post(
        "/api/bookings", json={"session_id": future_session, "member_id": aid}
    )
    body = staff_logged_in.get(f"/api/bookings?member_id={aid}").get_json()
    assert body["meta"]["total"] == 1


def test_invalid_status_filter(staff_logged_in):
    assert staff_logged_in.get("/api/bookings?status=foo").status_code == 400


# ---------- cancel ----------

def test_member_cancels_own(alice_logged_in, future_session):
    created = alice_logged_in.post(
        "/api/bookings", json={"session_id": future_session}
    ).get_json()
    resp = alice_logged_in.post(f"/api/bookings/{created['id']}/cancel")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "cancelled"


def test_cancel_not_found(alice_logged_in):
    assert alice_logged_in.post("/api/bookings/9999/cancel").status_code == 404


def test_cancel_cutoff_member_blocked_admin_ok(
    client, alice_year_card, class_def, do_login, app
):
    """30 分钟后开课：会员取消 400；admin 取消 200。"""
    from datetime import datetime, timedelta

    from app.extensions import db
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
        s_id = s.id

    do_login("alice", "member123")
    created = client.post("/api/bookings", json={"session_id": s_id}).get_json()
    resp = client.post(f"/api/bookings/{created['id']}/cancel")
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "cancel_cutoff_passed"
    client.post("/api/auth/logout")

    do_login("admin", "admin123")
    resp = client.post(f"/api/bookings/{created['id']}/cancel")
    assert resp.status_code == 200
