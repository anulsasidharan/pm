from __future__ import annotations

import os
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, status

AUTH_WINDOW_SECONDS = int(os.getenv("PM_AUTH_WINDOW_SECONDS", "300"))
AUTH_MAX_ATTEMPTS_PER_IP = int(os.getenv("PM_AUTH_MAX_ATTEMPTS_PER_IP", "30"))
AUTH_LOCKOUT_THRESHOLD = int(os.getenv("PM_AUTH_LOCKOUT_THRESHOLD", "5"))
AUTH_LOCKOUT_SECONDS = int(os.getenv("PM_AUTH_LOCKOUT_SECONDS", "900"))

_lock = threading.Lock()
_ip_attempts: dict[str, list[float]] = defaultdict(list)
_user_failures: dict[str, list[float]] = defaultdict(list)
_user_lock_until: dict[str, float] = {}


def _prune_recent(timestamps: list[float], now: float, window_seconds: int) -> list[float]:
    return [ts for ts in timestamps if now - ts <= window_seconds]


def assert_not_rate_limited(client_ip: str) -> None:
    now = time.time()

    with _lock:
        attempts = _prune_recent(_ip_attempts[client_ip], now, AUTH_WINDOW_SECONDS)
        if len(attempts) >= AUTH_MAX_ATTEMPTS_PER_IP:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many authentication attempts. Please try again later.",
            )

        attempts.append(now)
        _ip_attempts[client_ip] = attempts


def assert_not_locked(username: str) -> None:
    now = time.time()

    with _lock:
        locked_until = _user_lock_until.get(username)
        if locked_until and locked_until > now:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail="Account is temporarily locked due to failed login attempts.",
            )


def register_auth_failure(username: str) -> bool:
    now = time.time()

    with _lock:
        failures = _prune_recent(_user_failures[username], now, AUTH_WINDOW_SECONDS)
        failures.append(now)
        _user_failures[username] = failures

        if len(failures) >= AUTH_LOCKOUT_THRESHOLD:
            _user_lock_until[username] = now + AUTH_LOCKOUT_SECONDS
            _user_failures[username] = []
            return True

        return False


def register_auth_success(username: str) -> None:
    with _lock:
        _user_failures.pop(username, None)
        _user_lock_until.pop(username, None)


def reset_security_state() -> None:
    with _lock:
        _ip_attempts.clear()
        _user_failures.clear()
        _user_lock_until.clear()
