import sqlite3
from pathlib import Path

import pytest

from app.db import (
    create_password_reset_token,
    create_user,
    get_board_json,
    initialize_database,
    reset_password_with_token,
    save_board_json,
    verify_user_credentials,
)


def test_initialize_database_creates_file_and_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"

    created_path = initialize_database(db_path)

    assert created_path == db_path
    assert db_path.exists()

    conn = sqlite3.connect(db_path)
    try:
        user_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        board_table = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='boards'"
        ).fetchone()
    finally:
        conn.close()

    assert user_table is not None
    assert board_table is not None


def test_save_and_get_board_json_round_trip(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    payload = '{"columns":[{"id":"todo","cards":[]}]}'
    assert create_user("user", "password123", "user@example.com", db_path) is True

    save_board_json("user", payload, db_path)

    stored = get_board_json("user", db_path)
    assert stored == payload


def test_get_board_json_returns_none_for_missing_user(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"

    assert get_board_json("missing-user", db_path) is None


def test_save_board_json_rejects_invalid_json(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"

    with pytest.raises(ValueError):
        save_board_json("user", "not-json", db_path)


def test_create_user_and_verify_credentials(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"

    created = create_user("alice", "strong-password", "alice@example.com", db_path)

    assert created is True
    assert verify_user_credentials("alice", "strong-password", db_path) is True
    assert verify_user_credentials("alice", "wrong-password", db_path) is False


def test_create_user_returns_false_for_duplicate_username(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"

    assert create_user("alice", "strong-password", "alice@example.com", db_path) is True
    assert create_user("alice", "strong-password", "alice@example.com", db_path) is False


def test_create_user_returns_false_for_duplicate_email(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"

    assert create_user("alice", "strong-password", "alice@example.com", db_path) is True
    assert create_user("bob", "strong-password", "alice@example.com", db_path) is False


def test_password_reset_token_updates_password_once(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    assert create_user("alice", "old-password", "alice@example.com", db_path) is True
    assert create_password_reset_token("alice@example.com", "token-hash", db_path) is True

    assert reset_password_with_token("token-hash", "new-password", db_path) is True
    assert verify_user_credentials("alice", "new-password", db_path) is True
    assert reset_password_with_token("token-hash", "another-password", db_path) is False
