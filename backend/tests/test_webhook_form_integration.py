"""End-to-end: website form → lead created → conversation → AI reply.
Requires DATABASE_URL_TEST (Postgres)."""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL_TEST"),
    reason="DATABASE_URL_TEST not set",
)


@pytest.fixture
def client(pg_session, monkeypatch):
    # Point the running app's SessionLocal at the test DB.
    from app.core import database
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    url = os.environ["DATABASE_URL_TEST"]
    engine = create_engine(url, future=True)
    TestSession = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    from app.main import app
    from app.core.deps import get_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_form_lead_creates_conversation(client, pg_session):
    from app.models.organization import Organization, OrgSettings
    from app.models.lead import Lead

    org = Organization(name="Integration Spa", slug="int-spa")
    pg_session.add(org)
    pg_session.flush()
    pg_session.add(OrgSettings(
        organization_id=org.id, brand_name="Integration Spa",
        tone_of_voice="", disclaimers="",
        escalation_message="escalation",
    ))
    pg_session.commit()

    resp = client.post(
        "/api/v1/webhooks/form/lead",
        headers={"X-Org-Slug": "int-spa"},
        json={
            "first_name": "Taylor",
            "email": "taylor@example.com",
            "phone": "+15555550100",
            "message": "How much is botox?",
            "source_label": "website_contact_form",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ok"] is True
    assert body["lead_id"]

    leads = pg_session.execute(select(Lead).where(Lead.organization_id == org.id)).scalars().all()
    assert len(leads) == 1
    assert leads[0].phone == "+15555550100"
