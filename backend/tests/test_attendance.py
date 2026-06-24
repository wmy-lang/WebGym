"""``/api/attendance/*`` 测试。"""
from __future__ import annotations

import pytest


@pytest.fixture
def alice_with_booking(client, alice_year_card, future_session, do_login):
    """alice 已登录、已下一单。"""
    do_login("alice", "member123")
    created = client.post(
        "/api/bookings", json={"session_id": future_session}
    ).get_json()
    return client, created["id"]


def test_check_in_member_self(alice_with_booking):
    client, bid = alice_with_booking
    resp = client.post("/api/attendance", json={"booking_id": bid})
    assert resp.status_code == 201, resp.get_json()
    assert resp.get_json()["booking_id"] == bid


def test_check_in_admin_for_member(client, alice_year_card, future_session, do_login):
    do_login("alice", "member123")
    bid = client.post(
        "/api/bookings", json={"session_id": future_session}
    ).get_json()["id"]
    client.post("/api/auth/logout")

    do_login("staff01", "staff123")
    resp = client.post("/api/attendance", json={"booking_id": bid})
    assert resp.status_code == 201


def test_check_in_validation(alice_with_booking):
    client, _ = alice_with_booking
    resp = client.post("/api/attendance", json={})
    assert resp.status_code == 400


def test_check_in_not_found(alice_with_booking):
    client, _ = alice_with_booking
    resp = client.post("/api/attendance", json={"booking_id": 9999})
    assert resp.status_code == 404


def test_check_in_duplicate(alice_with_booking):
    client, bid = alice_with_booking
    client.post("/api/attendance", json={"booking_id": bid})
    resp = client.post("/api/attendance", json={"booking_id": bid})
    assert resp.status_code == 409
    assert resp.get_json()["error"] == "already_checked_in"


def test_member_list_attendance_self_only(alice_with_booking):
    client, bid = alice_with_booking
    client.post("/api/attendance", json={"booking_id": bid})

    body = client.get("/api/attendance").get_json()
    assert body["meta"]["total"] == 1


def test_staff_filter_attendance_by_session(client, alice_year_card, future_session, do_login):
    do_login("alice", "member123")
    bid = client.post(
        "/api/bookings", json={"session_id": future_session}
    ).get_json()["id"]
    client.post("/api/attendance", json={"booking_id": bid})
    client.post("/api/auth/logout")

    do_login("staff01", "staff123")
    body = client.get(f"/api/attendance?session_id={future_session}").get_json()
    assert body["meta"]["total"] == 1
