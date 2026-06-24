"""会员 CRUD 测试。"""
from __future__ import annotations

import pytest


@pytest.fixture
def staff_client(client, seeded_users, do_login):
    do_login("staff01", "staff123")
    return client


@pytest.fixture
def admin_client(client, seeded_users, do_login):
    do_login("admin", "admin123")
    return client


@pytest.fixture
def member_client(client, seeded_users, do_login):
    do_login("alice", "member123")
    return client


# ---------- 列表 ----------

def test_list_members_requires_staff(client):
    assert client.get("/api/members").status_code == 401


def test_list_members_forbidden_for_member(member_client):
    assert member_client.get("/api/members").status_code == 403


def test_list_members_returns_seeded(staff_client):
    resp = staff_client.get("/api/members")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["meta"]["total"] == 1  # 只有 alice
    assert body["items"][0]["username"] == "alice"
    assert body["items"][0]["real_name"] == "张爱丽"


def test_list_members_search_by_phone(staff_client):
    resp = staff_client.get("/api/members?q=13900000001")
    assert resp.status_code == 200
    assert resp.get_json()["meta"]["total"] == 1


def test_list_members_pagination(staff_client):
    resp = staff_client.get("/api/members?page=1&per_page=5")
    assert resp.status_code == 200
    meta = resp.get_json()["meta"]
    assert meta["page"] == 1 and meta["per_page"] == 5


# ---------- 创建 ----------

def test_create_member_happy_path(staff_client):
    resp = staff_client.post(
        "/api/members",
        json={
            "username": "bob",
            "password": "bob12345",
            "real_name": "鲍博",
            "phone": "13800000002",
            "gender": "male",
        },
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["username"] == "bob"
    assert body["real_name"] == "鲍博"
    assert body["role"] == "member"


def test_create_member_validation_missing_fields(staff_client):
    resp = staff_client.post("/api/members", json={"username": "x"})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_create_member_duplicate_username(staff_client):
    resp = staff_client.post(
        "/api/members",
        json={
            "username": "alice",  # 已存在
            "password": "whatever1",
            "real_name": "another",
            "phone": "13900000099",
        },
    )
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "username_taken"


def test_create_member_duplicate_phone(staff_client):
    resp = staff_client.post(
        "/api/members",
        json={
            "username": "newone",
            "password": "whatever1",
            "real_name": "another",
            "phone": "13900000001",  # alice 已用
        },
    )
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "phone_taken"


# ---------- 详情 / 更新 / 删除 ----------

def test_retrieve_member(staff_client, app):
    from app.extensions import db
    from app.models import User

    with app.app_context():
        alice_id = db.session.query(User).filter_by(username="alice").one().id

    resp = staff_client.get(f"/api/members/{alice_id}")
    assert resp.status_code == 200
    assert resp.get_json()["username"] == "alice"


def test_retrieve_member_404(staff_client):
    assert staff_client.get("/api/members/9999").status_code == 404


def test_retrieve_non_member_404(staff_client, app):
    """admin 不是会员，按 member 查应当 404。"""
    from app.extensions import db
    from app.models import User

    with app.app_context():
        admin_id = db.session.query(User).filter_by(username="admin").one().id

    assert staff_client.get(f"/api/members/{admin_id}").status_code == 404


def test_update_member_real_name(staff_client, app):
    from app.extensions import db
    from app.models import User

    with app.app_context():
        alice_id = db.session.query(User).filter_by(username="alice").one().id

    resp = staff_client.patch(
        f"/api/members/{alice_id}", json={"real_name": "新名字", "note": "VIP"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["real_name"] == "新名字"
    assert resp.get_json()["note"] == "VIP"


def test_update_member_phone_conflict(staff_client, app):
    from app.extensions import db
    from app.models import User

    # 先创建第二个会员
    staff_client.post(
        "/api/members",
        json={
            "username": "carol",
            "password": "abc12345",
            "real_name": "卡罗尔",
            "phone": "13800000003",
        },
    )

    with app.app_context():
        alice_id = db.session.query(User).filter_by(username="alice").one().id

    resp = staff_client.patch(
        f"/api/members/{alice_id}", json={"phone": "13800000003"}
    )
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "phone_taken"


def test_soft_delete_member(staff_client, app):
    from app.extensions import db
    from app.models import User

    with app.app_context():
        alice_id = db.session.query(User).filter_by(username="alice").one().id

    resp = staff_client.delete(f"/api/members/{alice_id}")
    assert resp.status_code == 200

    # 默认列表不含已禁用
    listing = staff_client.get("/api/members").get_json()
    assert listing["meta"]["total"] == 0

    # include_inactive=1 可以查到
    listing = staff_client.get("/api/members?include_inactive=1").get_json()
    assert listing["meta"]["total"] == 1
    assert listing["items"][0]["is_active"] is False
