from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from pathlib import Path

from app.auth import hash_password, verify_password


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
                email TEXT,
                password_hash TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        columns = {
            str(row[1])
            for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }
        if "email" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON users(email) WHERE email IS NOT NULL"
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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                used_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.commit()

    return resolved_path


def _ensure_user(conn: sqlite3.Connection, username: str) -> int:
    row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if row is None:
        raise RuntimeError("User does not exist")
    return int(row[0])


def create_user(username: str, password: str, email: str | None = None, db_path: Path | None = None) -> bool:
    resolved_path = initialize_database(db_path)
    password_hash = hash_password(password)
    normalized_email = email.strip().lower() if email else None

    with _connect(resolved_path) as conn:
        cursor = conn.execute(
            "INSERT OR IGNORE INTO users(username, email, password_hash) VALUES(?, ?, ?)",
            (username, normalized_email, password_hash),
        )
        conn.commit()
        return cursor.rowcount == 1


def verify_user_credentials(
    username: str,
    password: str,
    db_path: Path | None = None,
) -> bool:
    resolved_path = initialize_database(db_path)

    with _connect(resolved_path) as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()

    if row is None:
        return False

    password_hash = str(row[0])
    if not password_hash:
        return False

    return verify_password(password, password_hash)


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


def create_password_reset_token(email: str, token_hash: str, db_path: Path | None = None) -> bool:
    resolved_path = initialize_database(db_path)
    normalized_email = email.strip().lower()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")

    with _connect(resolved_path) as conn:
        user_row = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (normalized_email,),
        ).fetchone()
        if user_row is None:
            return False

        user_id = int(user_row[0])
        conn.execute(
            "INSERT INTO password_reset_tokens(user_id, token_hash, expires_at) VALUES(?, ?, ?)",
            (user_id, token_hash, expires_at),
        )
        conn.commit()
        return True


def reset_password_with_token(token_hash: str, new_password: str, db_path: Path | None = None) -> bool:
    resolved_path = initialize_database(db_path)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_hash = hash_password(new_password)

    with _connect(resolved_path) as conn:
        row = conn.execute(
            """
            SELECT id, user_id, expires_at, used_at
            FROM password_reset_tokens
            WHERE token_hash = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (token_hash,),
        ).fetchone()

        if row is None:
            return False

        token_id = int(row[0])
        user_id = int(row[1])
        expires_at = str(row[2])
        used_at = row[3]

        if used_at is not None or expires_at < now:
            return False

        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))
        conn.execute(
            "UPDATE password_reset_tokens SET used_at = ? WHERE id = ?",
            (now, token_id),
        )
        conn.commit()
        return True
