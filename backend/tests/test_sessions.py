"""排课 ``/api/sessions/*`` 测试。"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest


@pytest.fixture
def staff_client(client, seeded_users, class_def, do_login):
    do_login("staff01", "staff123")
    return client


@pytest.fixture
def member_client(client, seeded_users, class_def, do_login):
    do_login("alice", "member123")
    return client


def _future(hours: int = 24) -> str:
    return (datetime.utcnow() + timedelta(hours=hours)).isoformat()


# ---------- 创建 ----------

def test_create_session_inherits_duration_and_capacity(staff_client, class_def):
    start = _future(24)
    resp = staff_client.post(
        "/api/sessions", json={"class_def_id": class_def, "start_at": start}
    )
    assert resp.status_code == 201, resp.get_json()
    body = resp.get_json()
    assert body["class_name"] == "瑜伽入门"
    assert body["coach_name"] == "李教练"
    assert body["capacity"] == 5
    # end_at 应该 = start_at + 60min
    start_dt = datetime.fromisoformat(body["start_at"])
    end_dt = datetime.fromisoformat(body["end_at"])
    assert (end_dt - start_dt).total_seconds() == 60 * 60
    assert body["booked_count"] == 0
    assert body["status"] == "scheduled"


def test_create_session_explicit_end(staff_client, class_def):
    start = _future(24)
    end = (datetime.utcnow() + timedelta(hours=26)).isoformat()
    resp = staff_client.post(
        "/api/sessions",
        json={"class_def_id": class_def, "start_at": start, "end_at": end, "capacity": 8},
    )
    assert resp.status_code == 201
    assert resp.get_json()["capacity"] == 8


def test_create_session_end_before_start(staff_client, class_def):
    start = _future(48)
    end = _future(24)
    resp = staff_client.post(
        "/api/sessions",
        json={"class_def_id": class_def, "start_at": start, "end_at": end},
    )
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "validation_error"


def test_create_session_class_not_found(staff_client):
    resp = staff_client.post(
        "/api/sessions", json={"class_def_id": 9999, "start_at": _future(24)}
    )
    assert resp.status_code == 404


def test_create_session_requires_staff(member_client, class_def):
    resp = member_client.post(
        "/api/sessions", json={"class_def_id": class_def, "start_at": _future(24)}
    )
    assert resp.status_code == 403


# ---------- 列表过滤 ----------

def test_list_sessions_filter_by_date_range(staff_client, class_def):
    near = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    far = (datetime.utcnow() + timedelta(days=10)).isoformat()
    staff_client.post("/api/sessions", json={"class_def_id": class_def, "start_at": near})
    staff_client.post("/api/sessions", json={"class_def_id": class_def, "start_at": far})

    frm = datetime.utcnow().isoformat()
    to = (datetime.utcnow() + timedelta(days=1)).isoformat()
    resp = staff_client.get(f"/api/sessions?from={frm}&to={to}")
    assert resp.status_code == 200
    assert resp.get_json()["meta"]["total"] == 1


def test_list_sessions_invalid_datetime(staff_client):
    resp = staff_client.get("/api/sessions?from=not-a-date")
    assert resp.status_code == 400


def test_list_sessions_invalid_status(staff_client):
    resp = staff_client.get("/api/sessions?status=banana")
    assert resp.status_code == 400


def test_member_can_list_sessions(member_client, class_def):
    resp = member_client.get("/api/sessions")
    assert resp.status_code == 200


# ---------- update / cancel / finish ----------

def test_update_session(staff_client, class_def):
    s = staff_client.post(
        "/api/sessions", json={"class_def_id": class_def, "start_at": _future(24)}
    ).get_json()
    resp = staff_client.patch(
        f"/api/sessions/{s['id']}", json={"location": "A 教室", "capacity": 10}
    )
    assert resp.status_code == 200
    assert resp.get_json()["location"] == "A 教室"
    assert resp.get_json()["capacity"] == 10


def test_update_session_end_before_start(staff_client, class_def):
    s = staff_client.post(
        "/api/sessions", json={"class_def_id": class_def, "start_at": _future(24)}
    ).get_json()
    resp = staff_client.patch(
        f"/api/sessions/{s['id']}",
        json={
            "start_at": _future(48),
            "end_at": _future(24),
        },
    )
    assert resp.status_code == 400


def test_cancel_session(staff_client, class_def):
    s = staff_client.post(
        "/api/sessions", json={"class_def_id": class_def, "start_at": _future(24)}
    ).get_json()
    resp = staff_client.post(f"/api/sessions/{s['id']}/cancel")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "cancelled"

    # 再 cancel 应 400
    resp = staff_client.post(f"/api/sessions/{s['id']}/cancel")
    assert resp.status_code == 400


def test_finish_session(staff_client, class_def):
    s = staff_client.post(
        "/api/sessions", json={"class_def_id": class_def, "start_at": _future(24)}
    ).get_json()
    resp = staff_client.post(f"/api/sessions/{s['id']}/finish")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "finished"


def test_cannot_update_cancelled_session(staff_client, class_def):
    s = staff_client.post(
        "/api/sessions", json={"class_def_id": class_def, "start_at": _future(24)}
    ).get_json()
    staff_client.post(f"/api/sessions/{s['id']}/cancel")
    resp = staff_client.patch(f"/api/sessions/{s['id']}", json={"capacity": 9})
    assert resp.status_code == 400
    assert resp.get_json()["error"] == "session_not_scheduled"


def test_session_not_found(staff_client):
    assert staff_client.get("/api/sessions/9999").status_code == 404
    assert staff_client.post("/api/sessions/9999/cancel").status_code == 404
