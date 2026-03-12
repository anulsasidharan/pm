import json
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import initialize_database
from app.main import app


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("app.db.get_default_db_path", lambda: db_path)
    return db_path


def login(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"username": "user", "password": "password"},
    )
    assert response.status_code == 200


def test_auth_login_and_logout_cookie_lifecycle() -> None:
    with TestClient(app) as client:
        login(client)

        board_response = client.get("/api/board")
        assert board_response.status_code == 200

        logout_response = client.post("/api/auth/logout")
        assert logout_response.status_code == 200

        after_logout = client.get("/api/board")
        assert after_logout.status_code == 401


def test_register_creates_user_sets_cookie_and_allows_board_access() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/api/auth/register",
            json={"username": "newuser", "email": "newuser@example.com", "password": "strongpass123"},
        )

        assert register_response.status_code == 201
        assert register_response.json() == {"status": "created"}

        board_response = client.get("/api/board")
        assert board_response.status_code == 200


def test_register_rejects_duplicate_username_or_email() -> None:
    with TestClient(app) as client:
        first = client.post(
            "/api/auth/register",
            json={"username": "newuser", "email": "newuser@example.com", "password": "strongpass123"},
        )
        assert first.status_code == 201

        second = client.post(
            "/api/auth/register",
            json={"username": "newuser", "email": "newuser@example.com", "password": "anotherstrongpass"},
        )

    assert second.status_code == 409
    assert second.json()["detail"] == "Username or email already exists"


def test_login_works_for_registered_user() -> None:
    with TestClient(app) as client:
        register_response = client.post(
            "/api/auth/register",
            json={"username": "newuser", "email": "newuser@example.com", "password": "strongpass123"},
        )
        assert register_response.status_code == 201

        client.post("/api/auth/logout")

        login_response = client.post(
            "/api/auth/login",
            json={"username": "newuser", "password": "strongpass123"},
        )
        assert login_response.status_code == 200

        board_response = client.get("/api/board")
        assert board_response.status_code == 200


def test_get_board_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.get("/api/board")

    assert response.status_code == 401
    assert response.json()["detail"] == "Authentication required"


def test_get_board_returns_default_when_missing() -> None:
    with TestClient(app) as client:
        login(client)

        response = client.get("/api/board")

    assert response.status_code == 200
    assert response.json() == {"board": {"columns": []}}


def test_put_board_persists_and_get_returns_same_shape() -> None:
    payload = {
        "board": {
            "columns": [
                {
                    "id": "todo",
                    "name": "To Do",
                    "cards": [{"id": "c1", "title": "Ship Part 6"}],
                }
            ]
        }
    }

    with TestClient(app) as client:
        login(client)

        put_response = client.put("/api/board", json=payload)
        assert put_response.status_code == 200
        assert put_response.json() == payload

        get_response = client.get("/api/board")
        assert get_response.status_code == 200
        assert get_response.json() == payload


def test_put_board_rejects_malformed_payload() -> None:
    malformed_payload = {
        "board": {
            "columns": [
                {"id": "todo", "name": "To Do", "cards": [{"id": "c1"}]}
            ]
        }
    }

    with TestClient(app) as client:
        login(client)

        response = client.put("/api/board", json=malformed_payload)

    assert response.status_code == 422


def test_get_board_returns_500_when_stored_json_shape_is_invalid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "invalid.db"
    initialize_database(db_path)

    # Seed invalid board JSON shape directly to prove API-side validation.
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("INSERT INTO users(username, password_hash) VALUES(?, '')", ("user",))
        user_id = conn.execute("SELECT id FROM users WHERE username = ?", ("user",)).fetchone()[0]
        conn.execute(
            "INSERT INTO boards(user_id, board_json) VALUES(?, ?)",
            (user_id, json.dumps({"columns": [{"id": "todo"}]})),
        )
        conn.commit()
    finally:
        conn.close()

    with TestClient(app) as client:
        login(client)

        # Override fixture path for this test to hit the deliberately-invalid record.
        monkeypatch.setattr("app.db.get_default_db_path", lambda: db_path)
        response = client.get("/api/board")

    assert response.status_code == 500
    assert response.json()["detail"] == "Stored board data is invalid"
