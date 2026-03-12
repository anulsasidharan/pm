from __future__ import annotations

import os

from fastapi import HTTPException, Request, Response, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SESSION_COOKIE_NAME = "pm_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24


def _serializer() -> URLSafeTimedSerializer:
    secret = os.getenv("PM_SESSION_SECRET", "dev-only-session-secret")
    return URLSafeTimedSerializer(secret_key=secret, salt="pm-auth")


def create_session_token(username: str) -> str:
    return _serializer().dumps({"u": username})


def get_username_from_token(token: str) -> str | None:
    try:
        payload = _serializer().loads(token, max_age=SESSION_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None

    username = payload.get("u")
    if not isinstance(username, str) or not username:
        return None

    return username


def set_session_cookie(response: Response, username: str) -> None:
    token = create_session_token(username)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")


def require_authenticated_username(request: Request) -> str:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    username = get_username_from_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session",
        )

    return username
