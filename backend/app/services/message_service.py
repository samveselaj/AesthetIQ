"""Orchestrates saving a message, running rules + AI, sending the reply,
handling escalation, and scheduling follow-ups.

This is the heart of the inbound flow. Webhook handlers and manual inbox
sends both go through here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation, Message
from app.models.lead import Lead
from app.models.organization import OrgSettings
from app.services import ai_service
from app.services.booking_service import resolve_booking
from app.services.escalation_service import escalate
from app.services.lead_service import mark_inbound, mark_outbound
from app.services.outbound_service import send_outbound
from app.services.rules_engine import apply_rules
from app.services.treatment_normalizer import normalize_treatment
from app.services.twilio_service import send_sms

log = get_logger(__name__)


@dataclass
class InboundResult:
    inbound_message: Message
    outbound_message: Optional[Message]
    escalated: bool
    opt_out: bool


def record_inbound_and_respond(
    db: Session,
    *,
    organization_id: UUID,
    conversation: Conversation,
    lead: Lead,
    content: str,
    channel_type: str = "sms",
    raw_payload: Optional[dict[str, Any]] = None,
) -> InboundResult:
    """End-to-end handling of one inbound message."""
    inbound = Message(
        organization_id=organization_id,
        conversation_id=conversation.id,
        lead_id=lead.id,
        direction="inbound",
        sender_type="lead",
        channel_type=channel_type,
        content=content,
        raw_payload=raw_payload,
        delivery_status="received",
    )
    db.add(inbound)
    mark_inbound(lead)

    # Any inbound message flips the conversation back to "open" if it had been waiting
    if conversation.status in ("waiting_on_lead",):
        conversation.status = "open"
        db.add(conversation)

    # --- 1. Deterministic rules first -----------------------------------
    rule = apply_rules(content)

    if rule.opt_out:
        lead.do_not_contact = True
        lead.status = "closed_lost"
        conversation.status = "closed"
        conversation.ai_enabled = False
        db.add(lead)
        db.add(conversation)
        db.add(
            AuditLog(
                organization_id=organization_id,
                actor_type="system",
                action="opt_out",
                entity_type="lead",
                entity_id=lead.id,
            )
        )
        return InboundResult(
            inbound_message=inbound,
            outbound_message=None,
            escalated=False,
            opt_out=True,
        )

    # --- 2. Load org settings -------------------------------------------
    settings_row = db.query(OrgSettings).filter_by(organization_id=organization_id).one_or_none()
    ai_enabled = bool(
        conversation.ai_enabled
        and (settings_row.ai_enabled if settings_row else True)
    )
    auto_send = bool(settings_row.auto_send_replies if settings_row else True)

    # --- 3. Deterministic escalation forces a safe holding reply --------
    if rule.needs_escalation:
        safe_reply = (
            settings_row.escalation_message
            if settings_row
            else (
                "Thanks for your message. I'm flagging this for our team now so "
                "they can help you directly as soon as possible."
            )
        )
        outbound = send_outbound(
            db,
            organization_id=organization_id,
            conversation=conversation,
            lead=lead,
            content=safe_reply,
            channel_type=channel_type,
            ai_generated=False,
            send_sms_live=auto_send,
        )
        escalate(
            db,
            organization_id=organization_id,
            conversation=conversation,
            lead=lead,
            reason=rule.escalation_reason or "rules_escalation",
        )
        return InboundResult(
            inbound_message=inbound,
            outbound_message=outbound,
            escalated=True,
            opt_out=False,
        )

    # --- 4. AI classify + draft (if enabled) ----------------------------
    if not ai_enabled:
        # AI disabled — leave for staff, nothing automatic goes out.
        conversation.status = "waiting_on_staff"
        db.add(conversation)
        return InboundResult(
            inbound_message=inbound,
            outbound_message=None,
            escalated=False,
            opt_out=False,
        )

    classification = ai_service.classify_message(
        db,
        organization_id=organization_id,
        message=content,
        conversation_id=conversation.id,
        lead_id=lead.id,
    )

    # AI says escalate — trust it (it inherits rules) and send safe holding reply.
    if classification.needs_escalation:
        safe_reply = (
            settings_row.escalation_message
            if settings_row
            else (
                "Thanks for your message. I'm flagging this for our team now so "
                "they can help you directly as soon as possible."
            )
        )
        outbound = send_outbound(
            db,
            organization_id=organization_id,
            conversation=conversation,
            lead=lead,
            content=safe_reply,
            channel_type=channel_type,
            ai_generated=True,
            send_sms_live=auto_send,
        )
        escalate(
            db,
            organization_id=organization_id,
            conversation=conversation,
            lead=lead,
            reason=classification.escalation_reason or "ai_escalation",
        )
        return InboundResult(
            inbound_message=inbound,
            outbound_message=outbound,
            escalated=True,
            opt_out=False,
        )

    draft = ai_service.draft_reply(
        db,
        organization_id=organization_id,
        message=content,
        classification=classification,
        conversation_id=conversation.id,
        lead_id=lead.id,
    )

    # Apply treatment extraction to the lead for later analytics / booking
    treatment_key = classification.treatment_interest or normalize_treatment(content)
    if treatment_key and not lead.treatment_interest:
        lead.treatment_interest = treatment_key
        db.add(lead)

    # Build the final outbound body — append booking link if requested.
    body_parts = [draft.reply_text.strip()]
    booking_url: Optional[str] = None

    if draft.should_send_booking_link:
        resolution = resolve_booking(
            db,
            organization_id=organization_id,
            treatment_key=draft.booking_route_key or treatment_key,
            location_id=lead.location_id,
        )
        if resolution.url:
            booking_url = resolution.url
            body_parts.append(f"You can book here: {resolution.url}")
            lead.booking_status = "link_sent"
            db.add(lead)
        elif resolution.is_callback:
            body_parts.append(resolution.message)

    if draft.ask_followup_question and draft.followup_question:
        # Only append if the reply doesn't already end with a question.
        if not draft.reply_text.strip().endswith("?"):
            body_parts.append(draft.followup_question.strip())

    body = " ".join(p for p in body_parts if p).strip()

    # If auto-send is off, stage the reply as a staff-review draft instead of sending.
    outbound = send_outbound(
        db,
        organization_id=organization_id,
        conversation=conversation,
        lead=lead,
        content=body,
        channel_type=channel_type,
        ai_generated=True,
        send_sms_live=auto_send,
    )

    # After responding, we're waiting on the lead.
    if auto_send:
        conversation.status = "waiting_on_lead"
    else:
        conversation.status = "waiting_on_staff"
    db.add(conversation)

    return InboundResult(
        inbound_message=inbound,
        outbound_message=outbound,
        escalated=False,
        opt_out=False,
    )


def send_manual_reply(
    db: Session,
    *,
    organization_id: UUID,
    conversation: Conversation,
    lead: Lead,
    content: str,
    channel_type: str = "sms",
    actor_user_id: Optional[UUID] = None,
) -> Message:
    """Staff sending a manual message from the inbox UI."""
    outbound = Message(
        organization_id=organization_id,
        conversation_id=conversation.id,
        lead_id=lead.id,
        direction="outbound",
        sender_type="staff",
        channel_type=channel_type,
        content=content,
        ai_generated=False,
        reviewed_by_human=True,
        delivery_status="pending",
    )
    db.add(outbound)
    mark_outbound(lead)

    if channel_type == "sms" and lead.phone and not lead.do_not_contact:
        result = send_sms(to=lead.phone, body=content)
        outbound.delivery_status = result.status
        if result.error:
            outbound.raw_payload = {"error": result.error}
    else:
        outbound.delivery_status = "skipped_no_channel"

    conversation.status = "waiting_on_lead"
    db.add(conversation)
    db.add(outbound)

    db.add(
        AuditLog(
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            actor_type="user",
            action="send_manual_reply",
            entity_type="conversation",
            entity_id=conversation.id,
        )
    )
    return outbound
