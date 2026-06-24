"""认证 + 权限装饰器测试。"""
from __future__ import annotations

from datetime import datetime


# ---------- /api/auth/csrf-token ----------

def test_csrf_token_endpoint(client):
    resp = client.get("/api/auth/csrf-token")
    assert resp.status_code == 200
    assert isinstance(resp.get_json()["csrf_token"], str)


# ---------- /api/auth/login ----------

def test_login_success_returns_user_and_sets_cookie(client, seeded_users, do_login):
    resp = do_login("alice", "member123")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["user"]["username"] == "alice"
    assert body["user"]["role"] == "member"
    assert body["user"]["real_name"] == "张爱丽"
    assert "session=" in resp.headers.get("Set-Cookie", "")
    assert resp.headers.get("X-CSRFToken")


def test_login_wrong_password(client, seeded_users, do_login):
    resp = do_login("alice", "wrong")
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "invalid_credentials"}


def test_login_unknown_user(client, seeded_users, do_login):
    resp = do_login("ghost", "whatever")
    assert resp.status_code == 401


def test_login_missing_fields(client, seeded_users):
    resp = client.post("/api/auth/login", json={"username": ""})
    assert resp.status_code == 400


def test_login_disabled_account(client, seeded_users, do_login, app):
    from app.extensions import db
    from app.models import User

    with app.app_context():
        u = db.session.query(User).filter_by(username="alice").one()
        u.is_active = False
        db.session.commit()

    resp = do_login("alice", "member123")
    assert resp.status_code == 403
    assert resp.get_json() == {"error": "account_disabled"}


def test_login_updates_last_login_at(client, seeded_users, do_login, app):
    from app.extensions import db
    from app.models import User

    before = do_login("alice", "member123")
    assert before.status_code == 200

    with app.app_context():
        u = db.session.query(User).filter_by(username="alice").one()
        assert isinstance(u.last_login_at, datetime)


# ---------- /api/auth/me & logout ----------

def test_me_requires_login(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    assert resp.get_json() == {"error": "unauthorized"}


def test_me_returns_current_user(client, seeded_users, do_login):
    do_login("alice", "member123")
    resp = client.get("/api/auth/me")
    assert resp.status_code == 200
    assert resp.get_json()["user"]["username"] == "alice"


def test_logout_clears_session(client, seeded_users, do_login):
    do_login("alice", "member123")
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    me = client.get("/api/auth/me")
    assert me.status_code == 401


# ---------- @role_required ----------

def test_role_required_blocks_anonymous(client):
    assert client.get("/_probe/admin-only").status_code == 401
    assert client.get("/_probe/staff-only").status_code == 401
    assert client.get("/_probe/member-only").status_code == 401


def test_admin_required_allows_admin_blocks_others(client, seeded_users, do_login):
    do_login("admin", "admin123")
    assert client.get("/_probe/admin-only").status_code == 200
    client.post("/api/auth/logout")

    do_login("staff01", "staff123")
    assert client.get("/_probe/admin-only").status_code == 403
    client.post("/api/auth/logout")

    do_login("alice", "member123")
    assert client.get("/_probe/admin-only").status_code == 403


def test_staff_required_allows_admin_and_staff(client, seeded_users, do_login):
    do_login("admin", "admin123")
    assert client.get("/_probe/staff-only").status_code == 200
    client.post("/api/auth/logout")

    do_login("staff01", "staff123")
    assert client.get("/_probe/staff-only").status_code == 200
    client.post("/api/auth/logout")

    do_login("alice", "member123")
    assert client.get("/_probe/staff-only").status_code == 403


def test_member_required_blocks_admin(client, seeded_users, do_login):
    do_login("admin", "admin123")
    assert client.get("/_probe/member-only").status_code == 403
    client.post("/api/auth/logout")

    do_login("alice", "member123")
    assert client.get("/_probe/member-only").status_code == 200


def test_role_required_multi_role(client, seeded_users, do_login):
    """admin + member 同时允许；staff 不在白名单里 → 403。"""
    do_login("admin", "admin123")
    assert client.get("/_probe/any-role").status_code == 200
    client.post("/api/auth/logout")

    do_login("alice", "member123")
    assert client.get("/_probe/any-role").status_code == 200
    client.post("/api/auth/logout")

    do_login("staff01", "staff123")
    assert client.get("/_probe/any-role").status_code == 403
