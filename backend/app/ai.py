from __future__ import annotations

import os
from json import dumps
from typing import Any

import httpx

OPENROUTER_MODEL = "openai/gpt-oss-120b"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
AI_HISTORY_WINDOW = 20


class AIConfigError(Exception):
    pass


class AIUpstreamError(Exception):
    pass


def _extract_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise AIUpstreamError("AI response missing choices")

    message = choices[0].get("message")
    if not isinstance(message, dict):
        raise AIUpstreamError("AI response missing message")

    content = message.get("content")
    if isinstance(content, str):
        return content.strip()

    # Some providers can return structured content chunks.
    if isinstance(content, list):
        text_parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and isinstance(item.get("text"), str):
                text_parts.append(item["text"])
        if text_parts:
            return "\n".join(text_parts).strip()

    raise AIUpstreamError("AI response content was empty")


def _read_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except Exception:
        return f"OpenRouter request failed with status {response.status_code}"

    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
        if isinstance(payload.get("detail"), str):
            return payload["detail"]

    return f"OpenRouter request failed with status {response.status_code}"


def run_connectivity_check(prompt: str = "2+2") -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise AIConfigError("OPENROUTER_API_KEY is missing")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 128,
    }

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(OPENROUTER_URL, headers=headers, json=payload)
        except httpx.RequestError as exc:
            last_error = exc
            if attempt == 0:
                continue
            raise AIUpstreamError("Unable to reach OpenRouter") from exc

        if response.status_code >= 500 and attempt == 0:
            continue

        if response.status_code in (401, 403):
            raise AIConfigError(_read_error_message(response))

        if response.status_code >= 400:
            raise AIUpstreamError(_read_error_message(response))

        return _extract_text(response.json())

    if last_error is not None:
        raise AIUpstreamError("Unable to reach OpenRouter") from last_error

    raise AIUpstreamError("OpenRouter call failed")


def run_structured_board_chat(
    board_json: dict[str, Any],
    user_message: str,
    history: list[dict[str, str]],
) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise AIConfigError("OPENROUTER_API_KEY is missing")

    system_prompt = (
        "You are a project management assistant for a Kanban board. "
        "Always return STRICT JSON with this shape only: "
        '{"reply":"string","operation_type":"chat_only|board_update","board":null|{"columns":[{"id":"string","name":"string","cards":[{"id":"string","title":"string"}]}]}}. '
        "If no board changes are required, set operation_type to chat_only and board to null."
    )

    clipped_history = history[-AI_HISTORY_WINDOW:]
    history_lines = [f"{item['role']}: {item['content']}" for item in clipped_history]
    user_prompt = (
        "Current board JSON:\n"
        f"{dumps(board_json)}\n\n"
        "Conversation history (latest first not required):\n"
        f"{chr(10).join(history_lines) if history_lines else '(none)'}\n\n"
        f"User message: {user_message}"
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "max_tokens": 1200,
    }

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(OPENROUTER_URL, headers=headers, json=payload)
        except httpx.RequestError as exc:
            last_error = exc
            if attempt == 0:
                continue
            raise AIUpstreamError("Unable to reach OpenRouter") from exc

        if response.status_code >= 500 and attempt == 0:
            continue

        if response.status_code in (401, 403):
            raise AIConfigError(_read_error_message(response))

        if response.status_code >= 400:
            raise AIUpstreamError(_read_error_message(response))

        return _extract_text(response.json())

    if last_error is not None:
        raise AIUpstreamError("Unable to reach OpenRouter") from last_error

    raise AIUpstreamError("OpenRouter call failed")
