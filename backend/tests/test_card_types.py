"""卡类型 CRUD 测试。读 = staff；写 = admin。"""
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


def test_list_requires_staff(client):
    assert client.get("/api/card-types").status_code == 401


def test_list_forbidden_for_member(member_client):
    assert member_client.get("/api/card-types").status_code == 403


def test_create_forbidden_for_staff(staff_client):
    resp = staff_client.post(
        "/api/card-types",
        json={"name": "年卡", "duration_days": 365, "price": "1888.00"},
    )
    assert resp.status_code == 403


def test_create_card_type_happy_path(admin_client):
    resp = admin_client.post(
        "/api/card-types",
        json={"name": "年卡", "duration_days": 365, "price": "1888.00"},
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["name"] == "年卡"
    assert body["duration_days"] == 365
    assert body["price"] == "1888.00"


def test_create_card_type_needs_duration_or_visits(admin_client):
    resp = admin_client.post(
        "/api/card-types", json={"name": "怪卡", "price": "100.00"}
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_create_card_type_visit_count(admin_client):
    resp = admin_client.post(
        "/api/card-types",
        json={"name": "10 次卡", "total_visits": 10, "price": "299.00"},
    )
    assert resp.status_code == 201
    assert resp.get_json()["total_visits"] == 10


def test_create_card_type_name_taken(admin_client):
    admin_client.post(
        "/api/card-types",
        json={"name": "月卡", "duration_days": 30, "price": "299.00"},
    )
    resp = admin_client.post(
        "/api/card-types",
        json={"name": "月卡", "duration_days": 30, "price": "299.00"},
    )
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "name_taken"


def test_update_card_type(admin_client):
    created = admin_client.post(
        "/api/card-types",
        json={"name": "季卡", "duration_days": 90, "price": "699.00"},
    ).get_json()

    resp = admin_client.patch(
        f"/api/card-types/{created['id']}", json={"price": "799.00"}
    )
    assert resp.status_code == 200
    assert resp.get_json()["price"] == "799.00"


def test_soft_delete_card_type(admin_client):
    created = admin_client.post(
        "/api/card-types",
        json={"name": "周卡", "duration_days": 7, "price": "99.00"},
    ).get_json()

    assert admin_client.delete(f"/api/card-types/{created['id']}").status_code == 200
    listing = admin_client.get("/api/card-types").get_json()
    assert listing["meta"]["total"] == 0
    listing = admin_client.get("/api/card-types?include_inactive=1").get_json()
    assert listing["meta"]["total"] == 1


def test_staff_can_read_card_types(client, seeded_users, do_login):
    """权限矩阵：staff 读取列表 OK；admin 先建一个再切到 staff。"""
    do_login("admin", "admin123")
    client.post(
        "/api/card-types",
        json={"name": "半年卡", "duration_days": 180, "price": "999.00"},
    )
    client.post("/api/auth/logout")

    do_login("staff01", "staff123")
    resp = client.get("/api/card-types")
    assert resp.status_code == 200
    assert resp.get_json()["meta"]["total"] >= 1
