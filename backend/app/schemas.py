from __future__ import annotations

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


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
