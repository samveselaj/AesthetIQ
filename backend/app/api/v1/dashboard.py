from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter
from sqlalchemy import func, select

from app.core.deps import CurrentUser, DbSession
from app.models.conversation import Conversation, Message
from app.models.lead import Lead
from app.schemas.dashboard import DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _window_start(days: Optional[int]) -> datetime:
    """Return the UTC lower bound for a metric window.

    days=None (today): start of current UTC day.
    days=N: now - N days.
    """
    now = datetime.now(timezone.utc)
    if days is None:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    return now - timedelta(days=days)


def _collect_metrics(db, org_id, window_start: datetime) -> dict:
    def count(query):
        return db.execute(query).scalar_one()

    new_leads = count(
        select(func.count(Lead.id))
        .where(Lead.organization_id == org_id)
        .where(Lead.created_at >= window_start)
    )
    contacted = count(
        select(func.count(Lead.id))
        .where(Lead.organization_id == org_id)
        .where(Lead.last_outbound_at >= window_start)
    )
    booked = count(
        select(func.count(Lead.id))
        .where(Lead.organization_id == org_id)
        .where(Lead.status == "booked")
        .where(Lead.updated_at >= window_start)
    )
    escalated = count(
        select(func.count(Conversation.id))
        .where(Conversation.organization_id == org_id)
        .where(Conversation.escalation_state == "escalated")
        .where(Conversation.updated_at >= window_start)
    )
    inbox_open = count(
        select(func.count(Conversation.id))
        .where(Conversation.organization_id == org_id)
        .where(Conversation.status.in_(("open", "waiting_on_staff")))
    )
    link_sent = count(
        select(func.count(Lead.id))
        .where(Lead.organization_id == org_id)
        .where(Lead.booking_status == "link_sent")
        .where(Lead.updated_at >= window_start)
    )

    # Avg first response time: last_outbound - created, for leads created in window
    # and that have been responded to. Python-side — small window, acceptable.
    avg_seconds: Optional[float] = None
    rows = db.execute(
        select(Lead.id, Lead.created_at, Lead.last_outbound_at)
        .where(Lead.organization_id == org_id)
        .where(Lead.created_at >= window_start)
        .where(Lead.last_outbound_at.is_not(None))
    ).all()
    if rows:
        # Clamp negatives: a missed-call lead can have last_outbound_at recorded
        # before its created_at row was inserted (text-back fires before lead
        # row commits in some races) — treat those as zero rather than negative.
        deltas = [
            max(0.0, (r.last_outbound_at - r.created_at).total_seconds())
            for r in rows
        ]
        avg_seconds = sum(deltas) / len(deltas)

    return {
        "new_leads": new_leads,
        "contacted": contacted,
        "booked": booked,
        "escalated": escalated,
        "inbox_open": inbox_open,
        "link_sent": link_sent,
        "avg_first_response_seconds": avg_seconds,
    }


@router.get("/summary", response_model=DashboardSummary)
def summary(db: DbSession, user: CurrentUser) -> DashboardSummary:
    today = _collect_metrics(db, user.organization_id, _window_start(None))
    week_start = _window_start(7)
    org_id = user.organization_id

    def count(query):
        return db.execute(query).scalar_one()

    conversations_handled_7d = count(
        select(func.count(func.distinct(Message.conversation_id)))
        .where(Message.organization_id == org_id)
        .where(Message.created_at >= week_start)
    )
    missed_calls_recovered_7d = count(
        select(func.count(Lead.id))
        .where(Lead.organization_id == org_id)
        .where(Lead.source_type == "missed_call")
        .where(Lead.last_inbound_at >= week_start)
    )
    booking_links_sent_7d = count(
        select(func.count(Lead.id))
        .where(Lead.organization_id == org_id)
        .where(Lead.booking_status.in_(("link_sent", "booked")))
        .where(Lead.updated_at >= week_start)
    )
    booked_7d = count(
        select(func.count(Lead.id))
        .where(Lead.organization_id == org_id)
        .where(Lead.status == "booked")
        .where(Lead.updated_at >= week_start)
    )

    ai_total = count(
        select(func.count(Message.id))
        .where(Message.organization_id == org_id)
        .where(Message.created_at >= week_start)
        .where(Message.ai_generated.is_(True))
    )
    ai_in_escalated = count(
        select(func.count(Message.id))
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Message.organization_id == org_id)
        .where(Message.created_at >= week_start)
        .where(Message.ai_generated.is_(True))
        .where(Conversation.escalation_state == "escalated")
    )
    ai_handled: Optional[float] = None
    if ai_total > 0:
        ai_handled = round(100.0 * (1.0 - (ai_in_escalated / ai_total)), 1)

    return DashboardSummary(
        new_leads_today=today["new_leads"],
        contacted_today=today["contacted"],
        booked_today=today["booked"],
        escalated_today=today["escalated"],
        avg_first_response_seconds=today["avg_first_response_seconds"],
        inbox_open=today["inbox_open"],
        conversations_handled_7d=conversations_handled_7d,
        missed_calls_recovered_7d=missed_calls_recovered_7d,
        booking_links_sent_7d=booking_links_sent_7d,
        booked_7d=booked_7d,
        ai_handled_pct_7d=ai_handled,
    )
