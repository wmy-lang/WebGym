"""教练 CRUD 测试。"""
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


def test_list_coaches_requires_staff(client):
    assert client.get("/api/coaches").status_code == 401


def test_list_coaches_forbidden_for_member(member_client):
    assert member_client.get("/api/coaches").status_code == 403


def test_create_then_list_coach(staff_client):
    resp = staff_client.post(
        "/api/coaches",
        json={"name": "李教练", "gender": "male", "specialty": "瑜伽,普拉提"},
    )
    assert resp.status_code == 201, resp.get_json()
    coach_id = resp.get_json()["id"]

    listing = staff_client.get("/api/coaches").get_json()
    assert listing["meta"]["total"] == 1
    assert listing["items"][0]["id"] == coach_id


def test_create_coach_validation(staff_client):
    resp = staff_client.post("/api/coaches", json={})
    assert resp.status_code == 400


def test_update_coach(staff_client):
    create = staff_client.post("/api/coaches", json={"name": "王教练"})
    cid = create.get_json()["id"]

    resp = staff_client.patch(f"/api/coaches/{cid}", json={"specialty": "动感单车"})
    assert resp.status_code == 200
    assert resp.get_json()["specialty"] == "动感单车"


def test_search_coach_by_name(staff_client):
    staff_client.post("/api/coaches", json={"name": "张教练"})
    staff_client.post("/api/coaches", json={"name": "陈教练"})

    resp = staff_client.get("/api/coaches?q=张")
    assert resp.status_code == 200
    assert resp.get_json()["meta"]["total"] == 1


def test_soft_delete_coach(staff_client):
    create = staff_client.post("/api/coaches", json={"name": "刘教练"})
    cid = create.get_json()["id"]

    assert staff_client.delete(f"/api/coaches/{cid}").status_code == 200
    assert staff_client.get("/api/coaches").get_json()["meta"]["total"] == 0
    assert staff_client.get("/api/coaches?include_inactive=1").get_json()["meta"]["total"] == 1


def test_retrieve_coach_404(staff_client):
    assert staff_client.get("/api/coaches/9999").status_code == 404
