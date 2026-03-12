from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.ai import OPENROUTER_MODEL
from app.main import app


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("app.db.get_default_db_path", lambda: db_path)


def login(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200


def test_ai_check_missing_api_key_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with TestClient(app) as client:
        login(client)
        response = client.post("/api/ai/check", json={"prompt": "2+2"})

    assert response.status_code == 503
    assert "OPENROUTER_API_KEY is missing" in response.json()["detail"]


def test_ai_check_smoke_2_plus_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    captured: dict[str, object] = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "4"}}]}

    class FakeClient:
        def __init__(self, timeout: float):
            captured["timeout"] = timeout

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResponse()

    monkeypatch.setattr("app.ai.httpx.Client", FakeClient)

    with TestClient(app) as client:
        login(client)
        response = client.post("/api/ai/check", json={"prompt": "2+2"})

    assert response.status_code == 200
    assert response.json() == {"model": OPENROUTER_MODEL, "reply": "4"}
    payload = captured["json"]
    assert isinstance(payload, dict)
    assert payload["model"] == OPENROUTER_MODEL
    assert payload["messages"][0]["content"] == "2+2"


def test_ai_check_invalid_key_maps_to_503(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "bad-key")

    class FakeResponse:
        status_code = 401

        def json(self):
            return {"error": {"message": "Invalid API key"}}

    class FakeClient:
        def __init__(self, timeout: float):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers=None, json=None):
            return FakeResponse()

    monkeypatch.setattr("app.ai.httpx.Client", FakeClient)

    with TestClient(app) as client:
        login(client)
        response = client.post("/api/ai/check", json={"prompt": "2+2"})

    assert response.status_code == 503
    assert "Invalid API key" in response.json()["detail"]


def test_run_connectivity_check_retries_once_on_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    calls = {"count": 0}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "4"}}]}

    class FakeClient:
        def __init__(self, timeout: float):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, headers=None, json=None):
            calls["count"] += 1
            if calls["count"] == 1:
                from app.ai import httpx

                raise httpx.ReadTimeout("timed out")
            return FakeResponse()

    monkeypatch.setattr("app.ai.httpx.Client", FakeClient)

    from app.ai import run_connectivity_check

    reply = run_connectivity_check("2+2")
    assert reply == "4"
    assert calls["count"] == 2
