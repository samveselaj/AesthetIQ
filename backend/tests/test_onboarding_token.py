"""Onboarding requires a valid, unused, unexpired signup_token."""

import pytest


def test_onboarding_rejects_missing_token(pg_session):
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as c:
        r = c.post("/api/v1/onboarding", json={
            "org_name": "Foo",
            "org_slug": "foo",
            "admin_name": "X",
            "admin_email": "x@x.com",
            "admin_password": "hunter222",
            "location_name": "Main",
            "location_timezone": "UTC",
            "faqs": [],
            "booking_routes": [],
        })
    assert r.status_code == 401
