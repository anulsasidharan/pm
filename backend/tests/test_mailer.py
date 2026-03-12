import pytest

from app.mailer import MailConfigError, send_password_reset_email


@pytest.fixture(autouse=True)
def clear_mail_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("PM_MAIL_FROM", raising=False)
    monkeypatch.delenv("PM_APP_BASE_URL", raising=False)


def test_send_password_reset_email_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PM_MAIL_FROM", "onboarding@resend.dev")

    with pytest.raises(MailConfigError):
        send_password_reset_email("user@example.com", "token")


def test_send_password_reset_email_requires_from_email(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESEND_API_KEY", "re_test")

    with pytest.raises(MailConfigError):
        send_password_reset_email("user@example.com", "token")
