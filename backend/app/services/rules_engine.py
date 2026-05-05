"""Deterministic rules that run BEFORE and AROUND the AI. They are the safety
floor — the AI cannot override anything decided here.

Responsibilities:
- Detect STOP / unsubscribe → mark do_not_contact, halt automations
- Detect medical / complaint / urgent keywords → escalate
- Detect existing-client appointment keywords → escalate
- Detect "talk to human" asks → escalate
- Report whether we are inside business hours (informational — used by AI/templates)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional
from zoneinfo import ZoneInfo

STOP_WORDS: tuple[str, ...] = (
    "stop",
    "stopall",
    "unsubscribe",
    "cancel",
    "end",
    "quit",
    "opt out",
    "opt-out",
    "remove me",
)

# Clinical / safety → ALWAYS escalate
MEDICAL_KEYWORDS: tuple[str, ...] = (
    "swelling",
    "burn",
    "burning",
    "reaction",
    "allergic",
    "infection",
    "infected",
    "pain",
    "painful",
    "bruise",
    "bruising",
    "rash",
    "blister",
    "complication",
    "bleeding",
    "numb",
    "fever",
    "dizzy",
    "pregnant",
    "pregnancy",
    "breastfeeding",
    "nursing",
)

COMPLAINT_KEYWORDS: tuple[str, ...] = (
    "complaint",
    "refund",
    "unhappy",
    "lawyer",
    "attorney",
    "bbb",
    "yelp review",
    "terrible",
    "awful",
    "disappointed",
    "sue",
)

HUMAN_REQUEST_KEYWORDS: tuple[str, ...] = (
    "talk to a human",
    "talk to a person",
    "talk to someone",
    "speak to a manager",
    "get a manager",
    "need a manager",
    "real person",
    "not a bot",
    "call me back",
    "call me",
    "human please",
    "need a human",
    "get a human",
)

EXISTING_APPOINTMENT_KEYWORDS: tuple[str, ...] = (
    "reschedule",
    "re-schedule",
    "cancel my appointment",
    "cancel appointment",
    "move my appointment",
    "change my appointment",
    "i have an appointment",
    "my appointment",
)

URGENT_KEYWORDS: tuple[str, ...] = (
    "asap",
    "urgent",
    "emergency",
    "right now",
    "tonight",
    "today please",
)


@dataclass(frozen=True)
class RuleDecision:
    opt_out: bool = False
    needs_escalation: bool = False
    escalation_reason: Optional[str] = None
    urgent: bool = False
    existing_appointment: bool = False


def _contains_any(text: str, keywords: Iterable[str]) -> Optional[str]:
    for k in keywords:
        if k in text:
            return k
    return None


def apply_rules(message: str) -> RuleDecision:
    """Scan a single inbound message. Order matters — opt-out first, then
    medical, then other escalations."""
    norm = (message or "").strip().lower()

    # Tight STOP match: exact word or short-trim == keyword
    if norm in STOP_WORDS or _is_stop_exact(norm):
        return RuleDecision(opt_out=True)

    if hit := _contains_any(norm, MEDICAL_KEYWORDS):
        return RuleDecision(
            needs_escalation=True,
            escalation_reason=f"medical_keyword:{hit}",
        )

    if hit := _contains_any(norm, COMPLAINT_KEYWORDS):
        return RuleDecision(
            needs_escalation=True,
            escalation_reason=f"complaint_keyword:{hit}",
        )

    if hit := _contains_any(norm, EXISTING_APPOINTMENT_KEYWORDS):
        return RuleDecision(
            needs_escalation=True,
            escalation_reason=f"existing_appointment:{hit}",
            existing_appointment=True,
        )

    if hit := _contains_any(norm, HUMAN_REQUEST_KEYWORDS):
        return RuleDecision(
            needs_escalation=True,
            escalation_reason=f"human_request:{hit}",
        )

    urgent = _contains_any(norm, URGENT_KEYWORDS) is not None
    return RuleDecision(urgent=urgent)


_STOP_PATTERN = re.compile(r"^\s*(stop|stopall|unsubscribe|cancel|end|quit)\W*$", re.I)


def _is_stop_exact(norm: str) -> bool:
    return bool(_STOP_PATTERN.match(norm))


def is_within_business_hours(
    business_hours: Iterable,  # list[BusinessHours]
    tz: str = "America/New_York",
    now: Optional[datetime] = None,
) -> bool:
    """True if `now` is inside an open window. Closed-by-default if no rows set
    (front desk hasn't configured yet)."""
    rows = [h for h in business_hours]
    if not rows:
        return False

    now_local = (now or datetime.now(ZoneInfo(tz))).astimezone(ZoneInfo(tz))
    dow = now_local.weekday()
    today = [h for h in rows if h.day_of_week == dow]
    if not today:
        return False
    for h in today:
        if h.is_closed or not h.open_time or not h.close_time:
            continue
        t = now_local.time()
        if h.open_time <= t <= h.close_time:
            return True
    return False
