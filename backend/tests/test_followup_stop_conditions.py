"""Pure-python test of the follow-up stop-condition function — no DB needed."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.services.followup_service import should_run


def _job(kind: str):
    return SimpleNamespace(
        kind=kind,
        lead_id=uuid4(),
        conversation_id=uuid4(),
        status="pending",
        run_at=datetime.now(timezone.utc),
    )


def _lead(**kw):
    defaults = dict(
        do_not_contact=False,
        status="contacted",
        last_inbound_at=None,
        last_outbound_at=None,
        booking_status="not_sent",
    )
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def _convo(**kw):
    defaults = dict(status="waiting_on_lead", escalation_state="none")
    defaults.update(kw)
    return SimpleNamespace(**defaults)


def test_stops_if_opted_out():
    assert should_run(_lead(do_not_contact=True), _convo(), _job("no_reply_24h")) is False


def test_stops_if_booked():
    assert should_run(_lead(status="booked"), _convo(), _job("no_reply_24h")) is False


def test_stops_if_escalated():
    assert should_run(_lead(status="escalated"), _convo(escalation_state="escalated"), _job("no_reply_24h")) is False


def test_stops_if_lead_replied_since_outbound():
    now = datetime.now(timezone.utc)
    lead = _lead(
        last_outbound_at=now - timedelta(hours=2),
        last_inbound_at=now - timedelta(hours=1),  # after outbound
    )
    assert should_run(lead, _convo(), _job("no_reply_24h")) is False


def test_continues_if_no_reply():
    now = datetime.now(timezone.utc)
    lead = _lead(
        last_outbound_at=now - timedelta(hours=30),
        last_inbound_at=now - timedelta(hours=50),
    )
    assert should_run(lead, _convo(), _job("no_reply_24h")) is True


def test_no_booking_48h_stops_if_booked():
    assert should_run(
        _lead(booking_status="booked"),
        _convo(),
        _job("no_booking_48h"),
    ) is False
