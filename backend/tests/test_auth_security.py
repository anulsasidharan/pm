from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.security as security
from app.main import app
from app.observability import reset_metrics


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("app.db.get_default_db_path", lambda: db_path)
    security.reset_security_state()
    reset_metrics()
    return db_path


def test_login_rate_limit_blocks_excess_attempts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security, "AUTH_MAX_ATTEMPTS_PER_IP", 1)
    monkeypatch.setattr(security, "AUTH_WINDOW_SECONDS", 300)

    with TestClient(app) as client:
        first = client.post("/api/auth/login", json={"username": "user", "password": "wrong"})
        second = client.post("/api/auth/login", json={"username": "user", "password": "wrong"})

    assert first.status_code == 401
    assert second.status_code == 429


def test_account_lockout_triggers_after_repeated_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(security, "AUTH_LOCKOUT_THRESHOLD", 2)
    monkeypatch.setattr(security, "AUTH_WINDOW_SECONDS", 300)
    monkeypatch.setattr(security, "AUTH_LOCKOUT_SECONDS", 600)

    with TestClient(app) as client:
        _ = client.post("/api/auth/login", json={"username": "user", "password": "wrong"})
        _ = client.post("/api/auth/login", json={"username": "user", "password": "wrong"})
        locked_response = client.post("/api/auth/login", json={"username": "user", "password": "password"})

    assert locked_response.status_code == 423


def test_password_reset_flow_updates_password() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/api/auth/register",
            json={"username": "alice", "email": "alice@example.com", "password": "oldpass123"},
        )
        assert register_response.status_code == 201

        request_response = client.post(
            "/api/auth/password-reset/request",
            json={"email": "alice@example.com"},
        )
        assert request_response.status_code == 200
        token = request_response.json().get("dev_reset_token")
        assert isinstance(token, str)

        confirm_response = client.post(
            "/api/auth/password-reset/confirm",
            json={"token": token, "new_password": "newpass456"},
        )
        assert confirm_response.status_code == 200

        _ = client.post("/api/auth/logout")
        login_response = client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "newpass456"},
        )

    assert login_response.status_code == 200
