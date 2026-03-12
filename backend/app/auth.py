from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets

from fastapi import HTTPException, Request, Response, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SESSION_COOKIE_NAME = "pm_session"
SESSION_MAX_AGE_SECONDS = 60 * 60 * 24
PASSWORD_SALT_BYTES = 16
PASSWORD_ITERATIONS = 210_000
PASSWORD_ALGORITHM = "sha256"


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


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(PASSWORD_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        PASSWORD_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_{PASSWORD_ALGORITHM}${PASSWORD_ITERATIONS}${salt_b64}${digest_b64}"


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        scheme, iterations_str, salt_b64, digest_b64 = encoded_hash.split("$", 3)
    except ValueError:
        return False

    if scheme != f"pbkdf2_{PASSWORD_ALGORITHM}":
        return False

    try:
        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64)
        expected_digest = base64.b64decode(digest_b64)
    except Exception:
        return False

    candidate_digest = hashlib.pbkdf2_hmac(
        PASSWORD_ALGORITHM,
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate_digest, expected_digest)
