def test_health_returns_components():
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        r = c.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert "status" in body
    assert "components" in body
    assert "twilio" in body["components"]
    assert "openai" in body["components"]
