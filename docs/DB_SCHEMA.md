# Part 5 Schema: SQLite Model

## Goal

Store one board JSON payload per user for MVP, while keeping schema ready for multiple users later.

## Database File

- Path: `data/app.db`
- Auto-created on backend startup by `initialize_database()` in `backend/app/db.py`

## Tables

### `users`

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `username TEXT NOT NULL UNIQUE`
- `password_hash TEXT NOT NULL DEFAULT ''`
- `created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`

Notes:
- MVP login is hardcoded in frontend, but table exists now for multi-user support in later parts.
- `password_hash` is placeholder for future auth implementation.

### `boards`

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `user_id INTEGER NOT NULL UNIQUE`
- `board_json TEXT NOT NULL`
- `updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`
- `FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE`

Notes:
- `user_id` is `UNIQUE` so each user has exactly one board for MVP.
- `board_json` stores full board state as JSON text.

## Initialization Strategy

- On app startup, backend runs:
  - `CREATE TABLE IF NOT EXISTS users (...)`
  - `CREATE TABLE IF NOT EXISTS boards (...)`
- This creates DB and schema automatically if missing.

## Part 5 Test Coverage

`backend/tests/test_db.py` includes:
- DB file and schema creation test
- Board JSON save/read round-trip
- Missing-user read returns `None`
- Invalid JSON payload rejected
