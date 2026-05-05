from __future__ import annotations

import json

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.core.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.models.organization import Organization
from app.services.billing_service import handle_event, verify_signature

settings = get_settings()
router = APIRouter(prefix="/billing", tags=["billing"])


@router.post("/webhook")
async def lemonsqueezy_webhook(
    request: Request,
    db: DbSession,
    x_signature: str | None = Header(default=None, alias="X-Signature"),
    x_event_name: str | None = Header(default=None, alias="X-Event-Name"),
) -> dict:
    raw = await request.body()
    if not verify_signature(
        raw=raw,
        signature=x_signature or "",
        secret=settings.lemonsqueezy_signing_secret or "",
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid signature")
    body = json.loads(raw or b"{}")
    event_name = x_event_name or body.get("meta", {}).get("event_name") or ""
    handle_event(db, event_name, body)
    db.commit()
    return {"ok": True}


@router.get("/status")
def billing_status(db: DbSession, user: CurrentUser) -> dict:
    org = db.get(Organization, user.organization_id)
    return {
        "subscription_status": getattr(org, "subscription_status", "trialing"),
        "lemon_subscription_id": getattr(org, "lemon_subscription_id", None),
        "trial_ends_at": getattr(org, "trial_ends_at", None),
    }
