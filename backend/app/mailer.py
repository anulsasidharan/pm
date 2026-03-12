from __future__ import annotations

import os

import httpx

RESEND_API_URL = "https://api.resend.com/emails"


class MailConfigError(RuntimeError):
    pass


class MailDeliveryError(RuntimeError):
    pass


def _get_resend_api_key() -> str:
    key = os.getenv("RESEND_API_KEY", "").strip()
    if not key:
        raise MailConfigError("RESEND_API_KEY is not configured")
    return key


def _get_from_email() -> str:
    from_email = os.getenv("PM_MAIL_FROM", "").strip()
    if not from_email:
        raise MailConfigError("PM_MAIL_FROM is not configured")
    return from_email


def _get_app_base_url() -> str:
    return os.getenv("PM_APP_BASE_URL", "http://localhost:8000").rstrip("/")


def send_password_reset_email(to_email: str, token: str) -> None:
    api_key = _get_resend_api_key()
    from_email = _get_from_email()
    app_base_url = _get_app_base_url()
    reset_url = f"{app_base_url}/?mode=reset&token={token}"

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": "Reset your Project Management password",
        "html": (
            "<p>You requested a password reset.</p>"
            f"<p><a href=\"{reset_url}\">Reset your password</a></p>"
            "<p>If you did not request this, you can ignore this email.</p>"
        ),
        "text": (
            "You requested a password reset.\n\n"
            f"Reset your password: {reset_url}\n\n"
            "If you did not request this, you can ignore this email."
        ),
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(RESEND_API_URL, json=payload, headers=headers, timeout=15.0)
    except httpx.HTTPError as exc:
        raise MailDeliveryError("Password reset email request failed") from exc

    if response.status_code < 200 or response.status_code >= 300:
        raise MailDeliveryError(
            f"Resend API returned status {response.status_code}: {response.text}"
        )
