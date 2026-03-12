from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def get_default_db_path() -> Path:
    # Works locally (repo-root/data) and in Docker (/app/data).
    return Path(__file__).resolve().parents[2] / "data" / "app.db"


@contextmanager
def _connect(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
    finally:
        conn.close()


def initialize_database(db_path: Path | None = None) -> Path:
    resolved_path = db_path or get_default_db_path()

    with _connect(resolved_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS boards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                board_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.commit()

    return resolved_path


def _ensure_user(conn: sqlite3.Connection, username: str) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO users(username, password_hash) VALUES(?, '')",
        (username,),
    )
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if row is None:
        raise RuntimeError("Failed to ensure user row")
    return int(row[0])


def save_board_json(username: str, board_json: str, db_path: Path | None = None) -> None:
    # Store raw JSON text to keep MVP persistence simple.
    json.loads(board_json)

    resolved_path = initialize_database(db_path)

    with _connect(resolved_path) as conn:
        user_id = _ensure_user(conn, username)
        conn.execute(
            """
            INSERT INTO boards(user_id, board_json)
            VALUES(?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET board_json = excluded.board_json, updated_at = CURRENT_TIMESTAMP
            """,
            (user_id, board_json),
        )
        conn.commit()


def get_board_json(username: str, db_path: Path | None = None) -> str | None:
    resolved_path = initialize_database(db_path)

    with _connect(resolved_path) as conn:
        row = conn.execute(
            """
            SELECT b.board_json
            FROM boards b
            JOIN users u ON u.id = b.user_id
            WHERE u.username = ?
            """,
            (username,),
        ).fetchone()

    if row is None:
        return None

    return str(row[0])
