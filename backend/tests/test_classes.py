"""课程定义 ``/api/classes/*`` 测试。"""
from __future__ import annotations

import pytest


@pytest.fixture
def staff_client(client, seeded_users, do_login):
    do_login("staff01", "staff123")
    return client


@pytest.fixture
def member_client(client, seeded_users, do_login):
    do_login("alice", "member123")
    return client


def test_list_requires_login(client):
    assert client.get("/api/classes").status_code == 401


def test_create_class_happy_path(staff_client, coach):
    resp = staff_client.post(
        "/api/classes",
        json={"name": "动感单车", "coach_id": coach, "capacity": 20, "duration_minutes": 45},
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["name"] == "动感单车"
    assert body["coach_name"] == "李教练"


def test_create_class_validation_error(staff_client):
    resp = staff_client.post("/api/classes", json={})
    assert resp.status_code == 400


def test_create_class_unknown_coach(staff_client):
    resp = staff_client.post("/api/classes", json={"name": "X", "coach_id": 9999})
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "coach_not_found"


def test_member_can_read_active_classes(member_client, staff_client, coach):
    staff_client.post("/api/classes", json={"name": "瑜伽", "coach_id": coach})
    staff_client.post("/api/auth/logout")

    member_client.post(
        "/api/auth/login", json={"username": "alice", "password": "member123"}
    )
    listing = member_client.get("/api/classes").get_json()
    assert listing["meta"]["total"] == 1


def test_member_cannot_see_inactive(client, seeded_users, do_login, coach):
    do_login("staff01", "staff123")
    created = client.post(
        "/api/classes", json={"name": "瑜伽", "coach_id": coach}
    ).get_json()
    client.delete(f"/api/classes/{created['id']}")
    client.post("/api/auth/logout")

    do_login("alice", "member123")
    listing = client.get("/api/classes").get_json()
    assert listing["meta"]["total"] == 0
    # 直接访问详情也应 404
    assert client.get(f"/api/classes/{created['id']}").status_code == 404


def test_staff_include_inactive(staff_client, coach):
    created = staff_client.post(
        "/api/classes", json={"name": "瑜伽", "coach_id": coach}
    ).get_json()
    staff_client.delete(f"/api/classes/{created['id']}")
    listing = staff_client.get("/api/classes?include_inactive=1").get_json()
    assert listing["meta"]["total"] == 1


def test_update_class(staff_client, coach):
    created = staff_client.post(
        "/api/classes", json={"name": "瑜伽", "coach_id": coach}
    ).get_json()

    resp = staff_client.patch(
        f"/api/classes/{created['id']}", json={"capacity": 30, "description": "升级版"}
    )
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["capacity"] == 30
    assert body["description"] == "升级版"


def test_update_class_unknown_coach(staff_client, coach):
    created = staff_client.post(
        "/api/classes", json={"name": "瑜伽", "coach_id": coach}
    ).get_json()
    resp = staff_client.patch(f"/api/classes/{created['id']}", json={"coach_id": 9999})
    assert resp.status_code == 404


def test_search_by_name(staff_client, coach):
    staff_client.post("/api/classes", json={"name": "瑜伽入门", "coach_id": coach})
    staff_client.post("/api/classes", json={"name": "动感单车", "coach_id": coach})
    resp = staff_client.get("/api/classes?q=瑜伽")
    assert resp.status_code == 200
    assert resp.get_json()["meta"]["total"] == 1


def test_member_cannot_write(member_client, coach):
    resp = member_client.post("/api/classes", json={"name": "X", "coach_id": coach})
    assert resp.status_code == 403
