"""Match an incoming contact (phone / email) to an existing Lead within an org,
or create a new one. This is deliberately simple — MVP."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.lead import Lead

_PHONE_DIGITS = re.compile(r"\D+")


def normalize_phone(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    # keep leading +, strip everything else non-digit
    stripped = value.strip()
    has_plus = stripped.startswith("+")
    digits = _PHONE_DIGITS.sub("", stripped)
    if not digits:
        return None
    if has_plus:
        return "+" + digits
    # US numbers: if 10 digits, assume +1
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return digits


@dataclass
class LeadMatchResult:
    lead: Lead
    created: bool


def find_or_create_lead(
    db: Session,
    *,
    organization_id: UUID,
    source_type: str,
    source_label: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    full_name: Optional[str] = None,
    location_id: Optional[UUID] = None,
    treatment_interest: Optional[str] = None,
) -> LeadMatchResult:
    phone_norm = normalize_phone(phone)
    email_norm = (email or "").strip().lower() or None

    match_filters = []
    if phone_norm:
        match_filters.append(Lead.phone == phone_norm)
    if email_norm:
        match_filters.append(Lead.email == email_norm)

    existing: Optional[Lead] = None
    if match_filters:
        existing = db.execute(
            select(Lead)
            .where(Lead.organization_id == organization_id)
            .where(or_(*match_filters))
            .limit(1)
        ).scalars().first()

    if existing:
        # fill in missing info on second contact
        changed = False
        if phone_norm and not existing.phone:
            existing.phone = phone_norm
            changed = True
        if email_norm and not existing.email:
            existing.email = email_norm
            changed = True
        if first_name and not existing.first_name:
            existing.first_name = first_name
            changed = True
        if last_name and not existing.last_name:
            existing.last_name = last_name
            changed = True
        if full_name and not existing.full_name:
            existing.full_name = full_name
            changed = True
        if treatment_interest and not existing.treatment_interest:
            existing.treatment_interest = treatment_interest
            changed = True
        if location_id and not existing.location_id:
            existing.location_id = location_id
            changed = True
        if changed:
            db.add(existing)
        return LeadMatchResult(lead=existing, created=False)

    lead = Lead(
        organization_id=organization_id,
        location_id=location_id,
        source_type=source_type,
        source_label=source_label,
        first_name=first_name,
        last_name=last_name,
        full_name=full_name,
        phone=phone_norm,
        email=email_norm,
        treatment_interest=treatment_interest,
        status="new",
        lifecycle_stage="inquiry",
        booking_status="not_sent",
    )
    db.add(lead)
    db.flush()
    return LeadMatchResult(lead=lead, created=True)


def get_or_create_open_conversation(
    db: Session,
    *,
    organization_id: UUID,
    lead: Lead,
    channel_type: str,
) -> Conversation:
    convo = db.execute(
        select(Conversation)
        .where(Conversation.organization_id == organization_id)
        .where(Conversation.lead_id == lead.id)
        .where(Conversation.status.in_(("open", "waiting_on_lead", "waiting_on_staff")))
        .order_by(Conversation.created_at.desc())
        .limit(1)
    ).scalars().first()
    if convo:
        return convo
    convo = Conversation(
        organization_id=organization_id,
        lead_id=lead.id,
        channel_type=channel_type,
        status="open",
        ai_enabled=True,
        escalation_state="none",
    )
    db.add(convo)
    db.flush()
    return convo


def mark_inbound(lead: Lead) -> None:
    lead.last_inbound_at = datetime.now(timezone.utc)


def mark_outbound(lead: Lead) -> None:
    lead.last_outbound_at = datetime.now(timezone.utc)
    if lead.status == "new":
        lead.status = "contacted"
