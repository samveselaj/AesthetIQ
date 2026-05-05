"""Single helper that records and (optionally) sends an outbound message.

Lives in its own module so that both `message_service` and `followup_service`
can use it without circular imports.
"""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.conversation import Conversation, Message
from app.models.lead import Lead
from app.models.organization import Organization
from app.services.lead_service import mark_outbound
from app.services.twilio_service import send_sms


_DELINQUENT_STATUSES = {"past_due", "cancelled", "delinquent"}


def send_outbound(
    db: Session,
    *,
    organization_id: UUID,
    conversation: Conversation,
    lead: Lead,
    content: str,
    channel_type: str,
    ai_generated: bool,
    send_sms_live: bool,
) -> Message:
    msg = Message(
        organization_id=organization_id,
        conversation_id=conversation.id,
        lead_id=lead.id,
        direction="outbound",
        sender_type="ai" if ai_generated else "system",
        channel_type=channel_type,
        content=content,
        ai_generated=ai_generated,
        delivery_status="pending",
    )
    db.add(msg)
    mark_outbound(lead)

    org = db.get(Organization, organization_id)
    if org and org.subscription_status in _DELINQUENT_STATUSES:
        msg.delivery_status = "suspended_no_billing"
        db.add(msg)
        return msg

    if channel_type == "sms" and send_sms_live and lead.phone and not lead.do_not_contact:
        result = send_sms(to=lead.phone, body=content)
        msg.delivery_status = result.status
        if result.error:
            msg.raw_payload = {"error": result.error}
    elif not send_sms_live:
        msg.delivery_status = "draft"
    else:
        msg.delivery_status = "skipped_no_channel"

    db.add(msg)
    return msg
