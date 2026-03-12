import json
from pathlib import Path
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.ai import (
    AIConfigError,
    AIUpstreamError,
    OPENROUTER_MODEL,
    run_connectivity_check,
    run_structured_board_chat,
)
from app.auth import clear_session_cookie, require_authenticated_username, set_session_cookie
from app.db import get_board_json, initialize_database, save_board_json
from app.schemas import (
    AiConnectivityRequest,
    AiConnectivityResponse,
    AiChatRequest,
    AiChatResponse,
    Board,
    BoardResponse,
    BoardUpdateRequest,
    LoginRequest,
)

HARDCODED_USER = "user"
HARDCODED_PASSWORD = "password"
DEFAULT_BOARD = Board(columns=[])

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    yield


app = FastAPI(title="Project Management MVP API", lifespan=lifespan)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(payload: LoginRequest, response: Response) -> dict[str, str]:
    if payload.username != HARDCODED_USER or payload.password != HARDCODED_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    set_session_cookie(response, payload.username)
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
