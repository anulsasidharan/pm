from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_serves_hello_page() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Project Management MVP" in response.text


def test_metrics_endpoint_returns_counters() -> None:
    _ = client.get("/api/health")
    response = client.get("/api/metrics")

    assert response.status_code == 200
    payload = response.json()
    assert "total_requests" in payload
    assert "endpoint_status_counts" in payload
