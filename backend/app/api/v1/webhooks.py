"""Ingestion webhooks: Twilio SMS, Twilio voice-status (missed calls), website form.

These endpoints are UNAUTHENTICATED by design — they are called by external
providers. They must:
- validate shape / signature
- always record the raw payload in webhook_events
- resolve the correct organization
- hand off to message_service for the actual pipeline
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.deps import DbSession
from app.core.logging import get_logger
from app.models.audit_log import AuditLog
from app.models.conversation import Message
from app.models.location import Location
from app.models.organization import Organization
from app.models.webhook_event import WebhookEvent
from app.services.lead_service import (
    find_or_create_lead,
    get_or_create_open_conversation,
    normalize_phone,
)
from app.services.followup_service import schedule_default_followups
from app.services.message_service import record_inbound_and_respond
from app.services.outbound_service import send_outbound
from app.services.phi_scrub import scrub_phi
from app.services.treatment_normalizer import normalize_treatment
from app.services.twilio_service import send_sms, validate_twilio_signature

log = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ---------- Twilio SMS ----------


@router.post("/twilio/sms")
async def twilio_sms(
    request: Request,
    db: DbSession,
    x_twilio_signature: Optional[str] = Header(default=None),
) -> dict:
    form = dict(await request.form())
    url = str(request.url)

    if not validate_twilio_signature(
        url=url, params=form, signature_header=x_twilio_signature
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid Twilio signature")

    to_number = normalize_phone(form.get("To"))
    from_number = normalize_phone(form.get("From"))
    body = (form.get("Body") or "").strip()

    event = WebhookEvent(provider="twilio", event_type="sms.received", payload=scrub_phi(form))
    db.add(event)
    db.flush()

    if not to_number or not from_number or not body:
        event.processed = True
        event.error_message = "missing_fields"
        db.commit()
        return {"ok": False, "reason": "missing_fields"}

    if (
        settings.demo_twilio_number
        and to_number == normalize_phone(settings.demo_twilio_number)
    ):
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        cnt = db.execute(
            select(func.count(Message.id))
            .where(Message.direction == "inbound")
            .where(Message.channel_type == "sms")
            .where(Message.created_at >= cutoff)
            .where(Message.raw_payload["twilio"]["From"].astext == form.get("From", ""))
        ).scalar_one()
        if cnt >= settings.demo_max_messages_per_24h:
            send_sms(
                to=from_number,
                body=f"Demo limit reached — try the live product at {settings.app_url}",
            )
            event.processed = True
            event.error_message = "demo_rate_limited"
            db.commit()
            return {"ok": False, "reason": "demo_rate_limited"}

    org, location = _resolve_org_by_phone(db, to_number)
    if not org:
        event.processed = True
        event.error_message = "org_not_found"
        db.commit()
        log.warning("twilio_sms_org_not_found", to=to_number)
        return {"ok": False, "reason": "org_not_found"}
    event.organization_id = org.id

    match = find_or_create_lead(
        db,
        organization_id=org.id,
        source_type="sms",
        source_label="twilio_sms",
        phone=from_number,
        location_id=location.id if location else None,
        treatment_interest=normalize_treatment(body),
    )
    convo = get_or_create_open_conversation(
        db, organization_id=org.id, lead=match.lead, channel_type="sms"
    )
    result = record_inbound_and_respond(
        db,
        organization_id=org.id,
        conversation=convo,
        lead=match.lead,
        content=body,
        channel_type="sms",
        raw_payload=scrub_phi({"twilio": form}),
    )

    if match.created and not result.escalated and not result.opt_out:
        schedule_default_followups(
            db, organization_id=org.id, lead=match.lead, conversation=convo
        )

    event.processed = True
    db.commit()
    return {"ok": True, "lead_id": str(match.lead.id), "conversation_id": str(convo.id)}


# ---------- Twilio voice-status (missed call) ----------


@router.post("/twilio/voice-status")
async def twilio_voice_status(
    request: Request,
    db: DbSession,
    x_twilio_signature: Optional[str] = Header(default=None),
) -> dict:
    form = dict(await request.form())
    url = str(request.url)
    if not validate_twilio_signature(
        url=url, params=form, signature_header=x_twilio_signature
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Invalid Twilio signature")

    call_status = (form.get("CallStatus") or "").lower()
    missed = call_status in {"no-answer", "busy", "failed", "canceled"}

    event = WebhookEvent(provider="twilio", event_type=f"voice.{call_status or 'unknown'}", payload=scrub_phi(form))
    db.add(event)
    db.flush()

    if not missed:
        event.processed = True
        db.commit()
        return {"ok": True, "skipped": True}

    to_number = normalize_phone(form.get("To"))
    from_number = normalize_phone(form.get("From"))
    if not to_number or not from_number:
        event.processed = True
        event.error_message = "missing_fields"
        db.commit()
        return {"ok": False, "reason": "missing_fields"}

    org, location = _resolve_org_by_phone(db, to_number)
    if not org:
        event.processed = True
        event.error_message = "org_not_found"
        db.commit()
        return {"ok": False, "reason": "org_not_found"}
    event.organization_id = org.id

    match = find_or_create_lead(
        db,
        organization_id=org.id,
        source_type="missed_call",
        source_label="twilio_voice",
        phone=from_number,
        location_id=location.id if location else None,
    )
    convo = get_or_create_open_conversation(
        db, organization_id=org.id, lead=match.lead, channel_type="sms"
    )

    # Missed calls don't have an inbound message to classify. Send the scripted
    # recovery text directly and let the normal SMS flow take over once the
    # lead replies.
    brand = org.name
    body = (
        f"Sorry we missed your call to {brand}. I can help with treatment "
        "questions, pricing, availability, or booking. What are you interested in?"
    )
    send_outbound(
        db,
        organization_id=org.id,
        conversation=convo,
        lead=match.lead,
        content=body,
        channel_type="sms",
        ai_generated=False,
        send_sms_live=True,
    )

    if match.created:
        schedule_default_followups(
            db, organization_id=org.id, lead=match.lead, conversation=convo
        )

    event.processed = True
    db.commit()
    return {"ok": True, "lead_id": str(match.lead.id), "conversation_id": str(convo.id)}


# ---------- Website form ----------


class FormLeadPayload(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    message: Optional[str] = Field(default=None, max_length=4000)
    source_label: Optional[str] = "website_form"
    treatment_interest: Optional[str] = None


@router.post("/form/lead")
async def form_lead(
    payload: FormLeadPayload,
    db: DbSession,
    x_org_slug: Optional[str] = Header(default=None, alias="X-Org-Slug"),
    x_org_id: Optional[UUID] = Header(default=None, alias="X-Org-Id"),
) -> dict:
    if not (x_org_slug or x_org_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "X-Org-Slug or X-Org-Id required")

    stmt = select(Organization)
    if x_org_id:
        stmt = stmt.where(Organization.id == x_org_id)
    else:
        stmt = stmt.where(Organization.slug == x_org_slug)
    org = db.execute(stmt).scalar_one_or_none()
    if not org:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Organization not found")

    event = WebhookEvent(
        organization_id=org.id,
        provider="form",
        event_type="lead.submitted",
        payload=scrub_phi(payload.model_dump(mode="json")),
    )
    db.add(event)
    db.flush()

    match = find_or_create_lead(
        db,
        organization_id=org.id,
        source_type="form",
        source_label=payload.source_label,
        phone=payload.phone,
        email=str(payload.email) if payload.email else None,
        first_name=payload.first_name,
        last_name=payload.last_name,
        full_name=payload.full_name,
        treatment_interest=payload.treatment_interest
        or normalize_treatment(payload.message or ""),
    )
    convo = get_or_create_open_conversation(
        db, organization_id=org.id, lead=match.lead, channel_type="sms"
    )

    body = (payload.message or "").strip() or "(submitted website form)"
    result = record_inbound_and_respond(
        db,
        organization_id=org.id,
        conversation=convo,
        lead=match.lead,
        content=body,
        channel_type="sms",
        raw_payload=scrub_phi({"form": payload.model_dump(mode="json")}),
    )

    if match.created and not result.escalated and not result.opt_out:
        schedule_default_followups(
            db, organization_id=org.id, lead=match.lead, conversation=convo
        )

    db.add(
        AuditLog(
            organization_id=org.id,
            actor_type="system",
            action="form_lead_received",
            entity_type="lead",
            entity_id=match.lead.id,
            audit_metadata={"source_label": payload.source_label},
        )
    )
    event.processed = True
    db.commit()
    return {
        "ok": True,
        "lead_id": str(match.lead.id),
        "conversation_id": str(convo.id),
        "escalated": result.escalated,
    }


# ---------- helpers ----------


def _resolve_org_by_phone(db, phone: str) -> tuple[Optional[Organization], Optional[Location]]:
    loc = db.execute(
        select(Location).where(Location.phone_number == phone).limit(1)
    ).scalar_one_or_none()
    if loc:
        org = db.get(Organization, loc.organization_id)
        return org, loc
    return None, None
