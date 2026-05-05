"""Follow-up scheduling + stop conditions.

MVP sequence (overridable per-org via AutomationRule rows):
  +24h  — first follow-up if no response
  +72h  — second follow-up if no booking
  +7d   — final follow-up
Stop if: lead replies, books, conversation escalated, or lead opts out.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.automation import AutomationRule, MessageTemplate, ScheduledJob
from app.models.conversation import Conversation, Message
from app.models.lead import Lead
from app.services.outbound_service import send_outbound

log = get_logger(__name__)

DEFAULT_SEQUENCE_MINUTES: tuple[tuple[str, int, str], ...] = (
    ("no_reply_24h", 24 * 60, "Just checking in — would you like me to send the booking link for your consultation?"),
    ("no_booking_48h", 72 * 60, "We still have availability this week if you'd like to schedule."),
    ("no_reply_7d", 7 * 24 * 60, "If you'd prefer, our team can text or call you directly. Just let me know a good time."),
)


def schedule_default_followups(
    db: Session,
    *,
    organization_id: UUID,
    lead: Lead,
    conversation: Conversation,
) -> list[ScheduledJob]:
    now = datetime.now(timezone.utc)
    jobs: list[ScheduledJob] = []
    # Don't schedule if this lead has opted out or is already booked/escalated.
    if lead.do_not_contact or lead.status in ("booked", "escalated", "closed_lost"):
        return jobs

    for kind, minutes, _default_body in DEFAULT_SEQUENCE_MINUTES:
        job = ScheduledJob(
            organization_id=organization_id,
            lead_id=lead.id,
            conversation_id=conversation.id,
            kind=kind,
            run_at=now + timedelta(minutes=minutes),
            status="pending",
        )
        db.add(job)
        jobs.append(job)
    return jobs


def cancel_pending_followups(db: Session, lead_id: UUID) -> int:
    q = (
        select(ScheduledJob)
        .where(ScheduledJob.lead_id == lead_id)
        .where(ScheduledJob.status == "pending")
    )
    count = 0
    for job in db.execute(q).scalars().all():
        job.status = "cancelled"
        db.add(job)
        count += 1
    return count


def due_jobs(db: Session) -> Iterable[ScheduledJob]:
    now = datetime.now(timezone.utc)
    return (
        db.execute(
            select(ScheduledJob)
            .where(ScheduledJob.status == "pending")
            .where(ScheduledJob.run_at <= now)
            .order_by(ScheduledJob.run_at.asc())
            .limit(100)
        )
        .scalars()
        .all()
    )


def should_run(lead: Lead, conversation: Conversation, job: ScheduledJob) -> bool:
    if lead.do_not_contact:
        return False
    if lead.status in ("booked", "escalated", "closed_lost"):
        return False
    if conversation.status == "closed" or conversation.escalation_state == "escalated":
        return False
    # no_reply_* requires no inbound since the last outbound
    if job.kind in ("no_reply_24h", "no_reply_7d"):
        if lead.last_inbound_at and lead.last_outbound_at and lead.last_inbound_at > lead.last_outbound_at:
            return False
    if job.kind == "no_booking_48h" and lead.booking_status == "booked":
        return False
    return True


def render_followup_body(
    db: Session,
    organization_id: UUID,
    kind: str,
) -> str:
    # try to use a template
    template: Optional[MessageTemplate] = (
        db.execute(
            select(MessageTemplate)
            .where(MessageTemplate.organization_id == organization_id)
            .where(MessageTemplate.is_active.is_(True))
            .where(MessageTemplate.template_type == kind)
        )
        .scalars()
        .first()
    )
    if template:
        return template.content
    for k, _mins, body in DEFAULT_SEQUENCE_MINUTES:
        if k == kind:
            return body
    return "Just checking in — let me know if you'd like help scheduling."


def run_followup(db: Session, job: ScheduledJob) -> None:
    lead = db.get(Lead, job.lead_id)
    convo = db.get(Conversation, job.conversation_id) if job.conversation_id else None
    if not lead or not convo:
        job.status = "cancelled"
        db.add(job)
        return
    if not should_run(lead, convo, job):
        job.status = "cancelled"
        db.add(job)
        return

    body = render_followup_body(db, job.organization_id, job.kind)
    send_outbound(
        db,
        organization_id=job.organization_id,
        conversation=convo,
        lead=lead,
        content=body,
        channel_type=convo.channel_type,
        ai_generated=False,
        send_sms_live=True,
    )
    job.status = "sent"
    db.add(job)
