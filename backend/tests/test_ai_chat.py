from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

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


def test_ai_chat_chat_only_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    monkeypatch.setattr(
        "app.main.run_structured_board_chat",
        lambda board_json, user_message, history: '{"reply":"No changes needed","operation_type":"chat_only","board":null}',
    )

    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/api/ai/chat",
            json={
                "message": "What should I do next?",
                "history": [{"role": "assistant", "content": "Hi"}],
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "reply": "No changes needed",
        "operation_type": "chat_only",
        "board": None,
    }


def test_ai_chat_board_update_persists(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    monkeypatch.setattr(
        "app.main.run_structured_board_chat",
        lambda board_json, user_message, history: (
            '{"reply":"Added card","operation_type":"board_update","board":'
            '{"columns":[{"id":"todo","name":"To Do","cards":[{"id":"c-new","title":"New task"}]},'
            '{"id":"in-progress","name":"In Progress","cards":[]},'
            '{"id":"done","name":"Done","cards":[]}]}}'
        ),
    )

    with TestClient(app) as client:
        login(client)

        chat_response = client.post(
            "/api/ai/chat",
            json={"message": "Add a task to todo", "history": []},
        )
        assert chat_response.status_code == 200
        assert chat_response.json()["operation_type"] == "board_update"
        assert chat_response.json()["board"]["columns"][0]["cards"][0]["title"] == "New task"

        board_response = client.get("/api/board")
        assert board_response.status_code == 200
        assert board_response.json()["board"]["columns"][0]["cards"][0]["title"] == "New task"


def test_ai_chat_malformed_model_output_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    monkeypatch.setattr(
        "app.main.run_structured_board_chat",
        lambda board_json, user_message, history: "this is not json",
    )

    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/api/ai/chat",
            json={"message": "Please update board", "history": []},
        )

    assert response.status_code == 200
    assert response.json()["operation_type"] == "fallback_invalid_output"
    assert response.json()["board"] is None


def test_ai_chat_invalid_structured_shape_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    monkeypatch.setattr(
        "app.main.run_structured_board_chat",
        lambda board_json, user_message, history: '{"operation_type":"board_update","board":{"columns":[]}}',
    )

    with TestClient(app) as client:
        login(client)
        response = client.post(
            "/api/ai/chat",
            json={"message": "Please update board", "history": []},
        )

    assert response.status_code == 200
    assert response.json()["operation_type"] == "fallback_invalid_output"
    assert response.json()["reply"] == "I could not parse a structured response."
