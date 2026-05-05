"""LemonSqueezy webhook handling."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.organization import Organization
from app.models.signup_token import SignupToken
from app.services.email_service import send_email

log = get_logger(__name__)
settings = get_settings()


_EVENT_TO_STATUS = {
    "subscription_created": "active",
    "subscription_resumed": "active",
    "subscription_updated": "active",
    "subscription_cancelled": "cancelled",
    "subscription_paused": "past_due",
    "subscription_payment_failed": "past_due",
    "subscription_expired": "cancelled",
}


def status_for_event(event_name: str) -> Optional[str]:
    return _EVENT_TO_STATUS.get(event_name)


def verify_signature(*, raw: bytes, signature: str, secret: str) -> bool:
    if not secret or not signature:
        return False
    digest = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


def issue_signup_token(
    db: Session, *, email: str, lemon_subscription_id: str, plan: str
) -> SignupToken:
    tok = SignupToken(
        email=email.lower().strip(),
        token=secrets.token_urlsafe(32)[:64],
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        lemon_subscription_id=lemon_subscription_id,
        plan=plan,
    )
    db.add(tok)
    db.flush()
    return tok


def handle_event(db: Session, event_name: str, body: dict[str, Any]) -> None:
    """Apply a LemonSqueezy event to local state. Idempotent."""
    data = (body or {}).get("data") or {}
    attrs = (data.get("attributes") or {})
    sub_id = str(data.get("id") or attrs.get("subscription_id") or "")
    email = (attrs.get("user_email") or attrs.get("customer_email") or "").lower()
    variant_id = str(attrs.get("variant_id") or "")
    plan = "pro" if (
        settings.lemonsqueezy_variant_id_pro
        and variant_id == settings.lemonsqueezy_variant_id_pro
    ) else "starter"

    new_status = status_for_event(event_name)

    if event_name == "subscription_created":
        # Issue token and email it. Don't create the org — onboarding does that.
        if email:
            tok = issue_signup_token(
                db, email=email, lemon_subscription_id=sub_id, plan=plan
            )
            link = f"{settings.app_url}/onboarding?token={tok.token}"
            send_email(
                to=email,
                subject="Finish setting up your MedSpa Assistant workspace",
                html=(
                    f"<p>Thanks for subscribing! Click below to finish setup "
                    f"(link expires in 30 minutes):</p>"
                    f"<p><a href=\"{link}\">{link}</a></p>"
                ),
                text=f"Finish setup: {link} (expires in 30 minutes)",
            )
        return

    # For lifecycle events, find the org by lemon_subscription_id and update.
    if not sub_id or new_status is None:
        log.info("billing_event_ignored", event=event_name, sub_id=sub_id)
        return
    org = db.execute(
        select(Organization).where(Organization.lemon_subscription_id == sub_id)
    ).scalar_one_or_none()
    if org:
        org.subscription_status = new_status
        db.add(org)
