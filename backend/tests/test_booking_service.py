"""Integration-style test for the booking resolver — requires Postgres
(DATABASE_URL_TEST env). Skips cleanly if not configured."""

from __future__ import annotations

import uuid

import pytest

from app.models.booking_route import BookingRoute
from app.models.organization import Organization
from app.services.booking_service import resolve_booking


@pytest.fixture
def org(pg_session):
    org = Organization(name="Test Spa", slug=f"test-spa-{uuid.uuid4().hex[:8]}")
    pg_session.add(org)
    pg_session.flush()
    return org


def _route(**kwargs) -> BookingRoute:
    defaults = dict(
        route_type="consult",
        fallback_message="fallback",
        is_active=True,
    )
    defaults.update(kwargs)
    return BookingRoute(**defaults)


def test_exact_match_preferred(pg_session, org):
    pg_session.add(_route(
        organization_id=org.id,
        treatment_name="Botox",
        normalized_treatment_key="botox",
        booking_url="https://ex.com/botox",
    ))
    pg_session.add(_route(
        organization_id=org.id,
        treatment_name="General Consult",
        normalized_treatment_key="consultation_general",
        booking_url="https://ex.com/consult",
    ))
    pg_session.flush()

    r = resolve_booking(pg_session, organization_id=org.id, treatment_key="botox")
    assert r.url == "https://ex.com/botox"


def test_falls_back_to_consultation_general(pg_session, org):
    pg_session.add(_route(
        organization_id=org.id,
        treatment_name="General Consult",
        normalized_treatment_key="consultation_general",
        booking_url="https://ex.com/consult",
    ))
    pg_session.flush()

    r = resolve_booking(pg_session, organization_id=org.id, treatment_key="microneedling")
    assert r.url == "https://ex.com/consult"


def test_callback_when_no_routes(pg_session, org):
    r = resolve_booking(pg_session, organization_id=org.id, treatment_key="botox")
    assert r.is_callback is True
    assert r.url is None


def test_ignores_inactive(pg_session, org):
    pg_session.add(_route(
        organization_id=org.id,
        treatment_name="Botox",
        normalized_treatment_key="botox",
        booking_url="https://ex.com/botox-old",
        is_active=False,
    ))
    pg_session.flush()

    r = resolve_booking(pg_session, organization_id=org.id, treatment_key="botox")
    assert r.url is None
    assert r.is_callback is True
