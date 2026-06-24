def test_ping(client):
    resp = client.get("/api/ping")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "ok"
    assert body["service"] == "webgym-backend"
    assert body["config"] == "test"
    assert "time" in body


def test_404_returns_json(client):
    resp = client.get("/api/does-not-exist")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": "not_found"}
