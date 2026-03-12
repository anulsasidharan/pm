from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)


class PasswordResetConfirmRequest(BaseModel):
    token: str = Field(min_length=16, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)


class Card(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)


class Column(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    cards: list[Card]


class Board(BaseModel):
    columns: list[Column]


class BoardResponse(BaseModel):
    board: Board


class BoardUpdateRequest(BaseModel):
    board: Board


class AiConnectivityRequest(BaseModel):
    prompt: str = Field(default="2+2", min_length=1, max_length=2000)


class AiConnectivityResponse(BaseModel):
    model: str
    reply: str


class AiHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class AiChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[AiHistoryMessage] = Field(default_factory=list)


class AiChatResponse(BaseModel):
    reply: str
    operation_type: Literal["chat_only", "board_update", "fallback_invalid_output"]
    board: Board | None = None
