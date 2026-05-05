"""Mark a conversation as escalated, notify staff, and halt automation."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.audit_log import AuditLog
from app.models.conversation import Conversation
from app.models.escalation import EscalationRule
from app.models.lead import Lead
from app.services.email_service import send_email

log = get_logger(__name__)
settings = get_settings()


def escalate(
    db: Session,
    *,
    organization_id: UUID,
    conversation: Conversation,
    lead: Lead,
    reason: str,
) -> None:
    conversation.escalation_state = "escalated"
    conversation.status = "waiting_on_staff"
    conversation.ai_enabled = False
    lead.status = "escalated"
    db.add(conversation)
    db.add(lead)

    rules = (
        db.execute(
            select(EscalationRule)
            .where(EscalationRule.organization_id == organization_id)
            .where(EscalationRule.is_active.is_(True))
        )
        .scalars()
        .all()
    )

    for rule in rules:
        if rule.notify_email:
            send_email(
                to=rule.notify_email,
                subject=f"[AesthetIQ] Escalation: {reason}",
                html=_email_html(lead=lead, reason=reason, rule_name=rule.name),
                text=_email_text(lead=lead, reason=reason, rule_name=rule.name),
            )

    db.add(
        AuditLog(
            organization_id=organization_id,
            actor_type="system",
            action="escalate",
            entity_type="conversation",
            entity_id=conversation.id,
            audit_metadata={"reason": reason},
        )
    )


def _email_html(*, lead: Lead, reason: str, rule_name: str) -> str:
    name = lead.full_name or lead.first_name or lead.phone or lead.email or "a lead"
    dashboard = f"{settings.app_url}/inbox"
    return f"""
      <p>A conversation needs staff attention.</p>
      <ul>
        <li><b>Lead:</b> {name}</li>
        <li><b>Phone:</b> {lead.phone or '—'}</li>
        <li><b>Email:</b> {lead.email or '—'}</li>
        <li><b>Reason:</b> {reason}</li>
        <li><b>Rule:</b> {rule_name}</li>
      </ul>
      <p><a href="{dashboard}">Open inbox</a></p>
    """


def _email_text(*, lead: Lead, reason: str, rule_name: str) -> str:
    name = lead.full_name or lead.first_name or lead.phone or lead.email or "a lead"
    return (
        f"Escalation — {reason}\n"
        f"Lead: {name}\n"
        f"Phone: {lead.phone or '—'}\n"
        f"Email: {lead.email or '—'}\n"
        f"Rule: {rule_name}\n"
        f"Open: {settings.app_url}/inbox\n"
    )
