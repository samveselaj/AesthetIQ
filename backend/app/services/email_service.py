"""Thin email abstraction — Resend or SendGrid, stubbed when EMAIL_LIVE=false."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)
settings = get_settings()


@dataclass
class EmailResult:
    ok: bool
    provider_id: Optional[str] = None
    error: Optional[str] = None


def send_email(*, to: str, subject: str, html: str, text: Optional[str] = None) -> EmailResult:
    if not settings.email_live:
        log.info("email_stub", to=to, subject=subject)
        return EmailResult(ok=True, provider_id="simulated")

    if settings.email_provider == "resend" and settings.resend_api_key:
        return _send_resend(to=to, subject=subject, html=html, text=text)
    if settings.email_provider == "sendgrid" and settings.sendgrid_api_key:
        return _send_sendgrid(to=to, subject=subject, html=html, text=text)

    return EmailResult(ok=False, error="no email provider configured")


def _send_resend(*, to: str, subject: str, html: str, text: Optional[str]) -> EmailResult:
    try:
        resp = httpx.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.resend_api_key}"},
            json={
                "from": settings.email_from,
                "to": [to],
                "subject": subject,
                "html": html,
                **({"text": text} if text else {}),
            },
            timeout=10.0,
        )
        if resp.status_code >= 300:
            return EmailResult(ok=False, error=resp.text[:500])
        return EmailResult(ok=True, provider_id=resp.json().get("id"))
    except Exception as e:  # pragma: no cover
        return EmailResult(ok=False, error=str(e))


def _send_sendgrid(*, to: str, subject: str, html: str, text: Optional[str]) -> EmailResult:
    try:
        resp = httpx.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={
                "Authorization": f"Bearer {settings.sendgrid_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "personalizations": [{"to": [{"email": to}]}],
                "from": {"email": settings.email_from},
                "subject": subject,
                "content": [
                    {"type": "text/plain", "value": text or ""},
                    {"type": "text/html", "value": html},
                ],
            },
            timeout=10.0,
        )
        if resp.status_code >= 300:
            return EmailResult(ok=False, error=resp.text[:500])
        return EmailResult(ok=True)
    except Exception as e:  # pragma: no cover
        return EmailResult(ok=False, error=str(e))
