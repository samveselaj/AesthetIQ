"""Thin Twilio wrapper. When TWILIO_LIVE=false, we log outbound messages
instead of actually sending — safe for demos and CI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from app.core.config import get_settings
from app.core.logging import get_logger

log = get_logger(__name__)
settings = get_settings()


@dataclass
class SendResult:
    provider_message_id: Optional[str]
    status: str
    error: Optional[str] = None


def send_sms(*, to: str, body: str, from_number: Optional[str] = None) -> SendResult:
    sender = from_number or settings.twilio_from_number
    if not settings.twilio_live or not (
        settings.twilio_account_sid and settings.twilio_auth_token and sender
    ):
        log.info("sms_send_stub", to=to, body=body[:120])
        return SendResult(provider_message_id=None, status="simulated")

    try:
        from twilio.rest import Client

        client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
        msg = client.messages.create(body=body, from_=sender, to=to)
        return SendResult(provider_message_id=msg.sid, status=msg.status or "queued")
    except Exception as e:  # pragma: no cover — network/credential errors
        log.error("sms_send_failed", error=str(e))
        return SendResult(provider_message_id=None, status="failed", error=str(e))


def validate_twilio_signature(
    *, url: str, params: dict[str, str], signature_header: Optional[str]
) -> bool:
    if not settings.twilio_validate_signature:
        return True
    if not signature_header or not settings.twilio_auth_token:
        return False
    try:
        from twilio.request_validator import RequestValidator

        return RequestValidator(settings.twilio_auth_token).validate(
            url, params, signature_header
        )
    except Exception:  # pragma: no cover
        return False
