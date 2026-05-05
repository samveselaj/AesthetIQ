"""End-to-end tests for new conversation actions:
- POST /conversations/{id}/escalate     (manual escalate)
- POST /conversations/{id}/mark-lost    (staff closes as not-booked)

Covers: state transitions, pending follow-ups get cancelled, audit log entries.
Requires DATABASE_URL_TEST (Postgres)."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL_TEST"),
    reason="DATABASE_URL_TEST not set",
)


@pytest.fixture
def setup(pg_session):
    """Build a minimal org + user + lead + conversation inside the test DB, and
    return a TestClient with auth + db wired to that DB."""
    from app.core.database import get_db
    from app.core.deps import get_current_user
    from app.main import app
    from app.models.automation import ScheduledJob
    from app.models.conversation import Conversation
    from app.models.lead import Lead
    from app.models.organization import Organization, OrgSettings
    from app.models.user import User, UserRole

    url = os.environ["DATABASE_URL_TEST"]
    engine = create_engine(url, future=True)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    org = Organization(name="Test Spa", slug=f"test-{uuid4().hex[:8]}")
    pg_session.add(org)
    pg_session.flush()
    pg_session.add(
        OrgSettings(
            organization_id=org.id,
            brand_name="Test Spa",
            tone_of_voice="",
            disclaimers="",
            escalation_message="Thanks — flagging for our team.",
        )
    )
    user = User(
        organization_id=org.id,
        email=f"admin-{uuid4().hex[:6]}@test.local",
        password_hash="x",
        full_name="Admin",
        role=UserRole.SPA_ADMIN.value,
        is_active=True,
    )
    pg_session.add(user)
    lead = Lead(
        organization_id=org.id,
        source_type="sms",
        phone="+15555550199",
        status="contacted",
        lifecycle_stage="inquiry",
        booking_status="not_sent",
    )
    pg_session.add(lead)
    pg_session.flush()
    convo = Conversation(
        organization_id=org.id,
        lead_id=lead.id,
        channel_type="sms",
        status="open",
        ai_enabled=True,
        escalation_state="none",
    )
    pg_session.add(convo)
    # A pending follow-up that we expect to be cancelled by both actions.
    job = ScheduledJob(
        organization_id=org.id,
        lead_id=lead.id,
        conversation_id=convo.id,
        kind="no_reply_24h",
        run_at=datetime.now(timezone.utc) + timedelta(hours=24),
        status="pending",
    )
    pg_session.add(job)
    pg_session.commit()

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    def override_current_user():
        # Re-fetch the user in the request-scoped session so the ORM instance
        # is attached to the right session.
        db = TestSession()
        try:
            return db.get(User, user.id)
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user
    try:
        yield {
            "client": TestClient(app),
            "org_id": org.id,
            "user_id": user.id,
            "lead_id": lead.id,
            "conversation_id": convo.id,
            "job_id": job.id,
        }
    finally:
        app.dependency_overrides.clear()


def test_manual_escalate_flips_state_and_cancels_followups(setup, pg_session):
    from app.models.automation import ScheduledJob
    from app.models.conversation import Conversation
    from app.models.lead import Lead

    cid = setup["conversation_id"]
    resp = setup["client"].post(
        f"/api/v1/conversations/{cid}/escalate",
        json={"reason": "Lead asked for manager"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["escalation_state"] == "escalated"
    assert body["ai_enabled"] is False
    assert body["ai_mode"] == "escalated"

    pg_session.expire_all()
    convo = pg_session.get(Conversation, cid)
    lead = pg_session.get(Lead, setup["lead_id"])
    job = pg_session.get(ScheduledJob, setup["job_id"])
    assert convo.status == "waiting_on_staff"
    assert lead.status == "escalated"
    assert job.status == "cancelled"


def test_mark_lost_closes_and_cancels_followups(setup, pg_session):
    from app.models.automation import ScheduledJob
    from app.models.conversation import Conversation
    from app.models.lead import Lead

    cid = setup["conversation_id"]
    resp = setup["client"].post(
        f"/api/v1/conversations/{cid}/mark-lost",
        json={"reason": "ghosted"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "closed"
    assert body["ai_enabled"] is False
    assert body["ai_mode"] == "paused"

    pg_session.expire_all()
    lead = pg_session.get(Lead, setup["lead_id"])
    job = pg_session.get(ScheduledJob, setup["job_id"])
    assert lead.status == "closed_lost"
    assert lead.booking_status == "declined"
    assert job.status == "cancelled"


def test_mark_lost_preserves_booked_status(setup, pg_session):
    """If the lead already booked, mark-lost shouldn't downgrade booking_status."""
    from app.models.lead import Lead

    lead = pg_session.get(Lead, setup["lead_id"])
    lead.booking_status = "booked"
    pg_session.commit()

    cid = setup["conversation_id"]
    resp = setup["client"].post(
        f"/api/v1/conversations/{cid}/mark-lost",
        json={},
    )
    assert resp.status_code == 200, resp.text

    pg_session.expire_all()
    lead2 = pg_session.get(Lead, setup["lead_id"])
    assert lead2.booking_status == "booked"  # preserved
    assert lead2.status == "closed_lost"


def test_mark_booked_cancels_pending_followups(setup, pg_session):
    from app.models.automation import ScheduledJob
    from app.models.lead import Lead

    cid = setup["conversation_id"]
    resp = setup["client"].post(f"/api/v1/conversations/{cid}/mark-booked")
    assert resp.status_code == 200, resp.text

    pg_session.expire_all()
    lead = pg_session.get(Lead, setup["lead_id"])
    job = pg_session.get(ScheduledJob, setup["job_id"])
    assert lead.status == "booked"
    assert lead.booking_status == "booked"
    assert job.status == "cancelled"


def test_ai_mode_paused_after_takeover(setup, pg_session):
    from app.models.conversation import Conversation

    cid = setup["conversation_id"]
    resp = setup["client"].post(f"/api/v1/conversations/{cid}/takeover")
    assert resp.status_code == 200, resp.text
    assert resp.json()["ai_mode"] == "paused"

    resp2 = setup["client"].post(f"/api/v1/conversations/{cid}/release-ai")
    assert resp2.status_code == 200
    assert resp2.json()["ai_mode"] == "active"
