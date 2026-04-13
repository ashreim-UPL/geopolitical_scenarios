from fastapi.testclient import TestClient

from geostate_api.main import app


def test_health_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_meta_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/v1/meta")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "geostate-api"
    assert payload["version"] == "0.1.0"
    assert "timestamp_utc" in payload

