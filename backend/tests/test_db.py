import sqlite3
from pathlib import Path

import pytest

from app.db import get_board_json, initialize_database, save_board_json


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
