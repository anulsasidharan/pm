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
    assert "Kanban board preview" in response.text
    assert "Hello world from FastAPI inside Docker." in response.text
    assert "fetch('/api/health')" in response.text
