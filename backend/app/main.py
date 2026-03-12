import json
import hashlib
import os
import secrets
from pathlib import Path
from typing import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.staticfiles import StaticFiles

from app.ai import (
    AIConfigError,
    AIUpstreamError,
    OPENROUTER_MODEL,
    run_connectivity_check,
    run_structured_board_chat,
)
from app.auth import clear_session_cookie, require_authenticated_username, set_session_cookie
from app.db import (
    create_password_reset_token,
    create_user,
    get_board_json,
    initialize_database,
    reset_password_with_token,
    save_board_json,
    verify_user_credentials,
)
from app.observability import (
    get_metrics_snapshot,
    record_auth_failure,
    record_lockout,
    record_rate_limit,
    record_response,
)
from app.mailer import MailConfigError, MailDeliveryError, send_password_reset_email
from app.security import (
    assert_not_locked,
    assert_not_rate_limited,
    register_auth_failure,
    register_auth_success,
)
from app.schemas import (
    AiConnectivityRequest,
    AiConnectivityResponse,
    AiChatRequest,
    AiChatResponse,
    Board,
    BoardResponse,
    BoardUpdateRequest,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
)

HARDCODED_USER = "user"
HARDCODED_PASSWORD = "password"
HARDCODED_EMAIL = "user@example.com"
DEFAULT_BOARD = Board(columns=[])

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    create_user(HARDCODED_USER, HARDCODED_PASSWORD, HARDCODED_EMAIL)
    yield


app = FastAPI(title="Project Management MVP API", lifespan=lifespan)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
    except Exception:
        record_response(request.url.path, 500)
        raise

    record_response(request.url.path, response.status_code)
    return response


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/metrics")
def metrics() -> dict[str, object]:
    return get_metrics_snapshot()


@app.post("/api/auth/login")
def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, str]:
    client_ip = request.client.host if request.client else "unknown"

    try:
        assert_not_rate_limited(client_ip)
        assert_not_locked(payload.username)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            record_rate_limit()
        elif exc.status_code == status.HTTP_423_LOCKED:
            record_lockout()
        raise

    if not verify_user_credentials(payload.username, payload.password):
        record_auth_failure()
        locked = register_auth_failure(payload.username)
        if locked:
            record_lockout()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    register_auth_success(payload.username)
    set_session_cookie(response, payload.username)
    return {"status": "ok"}


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, response: Response) -> dict[str, str]:
    client_ip = request.client.host if request.client else "unknown"
    try:
        assert_not_rate_limited(client_ip)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            record_rate_limit()
        raise

    created = create_user(payload.username, payload.password, payload.email)
    if not created:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already exists",
        )

    set_session_cookie(response, payload.username)
    return {"status": "created"}


def _password_reset_dev_mode() -> bool:
    explicit = os.getenv("PM_DEV_EXPOSE_RESET_TOKEN")
    if explicit is not None:
        return explicit.strip().lower() in {"1", "true", "yes", "on"}

    return os.getenv("PM_ENV", "development").strip().lower() != "production"


@app.post("/api/auth/password-reset/request")
def password_reset_request(payload: PasswordResetRequest) -> dict[str, str]:
    reset_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(reset_token.encode("utf-8")).hexdigest()
    created = create_password_reset_token(payload.email, token_hash)

    # Do not reveal account existence to callers.
    if not created:
        return {"status": "ok"}

    try:
        send_password_reset_email(payload.email, reset_token)
    except (MailConfigError, MailDeliveryError) as exc:
        # In local/dev workflows, allow reset to proceed with dev token output.
        if not _password_reset_dev_mode():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Unable to send password reset email: {exc}",
            ) from exc

    if _password_reset_dev_mode():
        return {"status": "ok", "dev_reset_token": reset_token}

    return {"status": "ok"}


@app.post("/api/auth/password-reset/confirm")
def password_reset_confirm(payload: PasswordResetConfirmRequest) -> dict[str, str]:
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    updated = reset_password_with_token(token_hash, payload.new_password)

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    return {"status": "ok"}


@app.post("/api/auth/logout")
def logout(response: Response) -> dict[str, str]:
    clear_session_cookie(response)
    return {"status": "ok"}


@app.get("/api/board", response_model=BoardResponse)
def get_board(username: str = Depends(require_authenticated_username)) -> BoardResponse:
    stored = get_board_json(username)
    if stored is None:
        return BoardResponse(board=DEFAULT_BOARD)

    try:
        board = Board.model_validate_json(stored)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stored board data is invalid",
        ) from exc

    return BoardResponse(board=board)


@app.put("/api/board", response_model=BoardResponse)
def update_board(
    payload: BoardUpdateRequest,
    username: str = Depends(require_authenticated_username),
) -> BoardResponse:
    # Persist validated board payload for the signed-in user.
    save_board_json(username, json.dumps(payload.board.model_dump()))
    return BoardResponse(board=payload.board)


@app.post("/api/ai/check", response_model=AiConnectivityResponse)
def ai_connectivity_check(
    payload: AiConnectivityRequest,
    username: str = Depends(require_authenticated_username),
) -> AiConnectivityResponse:
    _ = username
    try:
        reply = run_connectivity_check(payload.prompt)
    except AIConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except AIUpstreamError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    return AiConnectivityResponse(model=OPENROUTER_MODEL, reply=reply)


@app.post("/api/ai/chat", response_model=AiChatResponse)
def ai_chat(
    payload: AiChatRequest,
    username: str = Depends(require_authenticated_username),
) -> AiChatResponse:
    stored = get_board_json(username)
    if stored is None:
        current_board = DEFAULT_BOARD
    else:
        try:
            current_board = Board.model_validate_json(stored)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored board data is invalid",
            ) from exc

    history_payload = [msg.model_dump() for msg in payload.history]
    try:
        raw_reply = run_structured_board_chat(
            board_json=current_board.model_dump(),
            user_message=payload.message,
            history=history_payload,
        )
    except AIConfigError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except AIUpstreamError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    try:
        parsed = json.loads(raw_reply)
    except Exception:
        return AiChatResponse(
            reply=raw_reply or "I could not parse a structured response.",
            operation_type="fallback_invalid_output",
            board=None,
        )

    try:
        structured = AiChatResponse.model_validate(parsed)
    except Exception:
        return AiChatResponse(
            reply="I could not parse a structured response.",
            operation_type="fallback_invalid_output",
            board=None,
        )

    if structured.operation_type == "board_update" and structured.board is not None:
        # Persist the full validated board snapshot atomically with single upsert write.
        save_board_json(username, json.dumps(structured.board.model_dump()))

    if structured.operation_type != "board_update":
        structured.board = None

    return structured


static_dir = Path(__file__).resolve().parent / "static"
app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")
