"""LemonSqueezy webhook signature verification + event mapping."""

import hashlib
import hmac
import json

import pytest


def test_signature_verifies_correctly():
    from app.services.billing_service import verify_signature

    secret = "topsecret"
    raw = b'{"event":"x"}'
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    assert verify_signature(raw=raw, signature=sig, secret=secret) is True


def test_signature_rejects_bad_sig():
    from app.services.billing_service import verify_signature

    assert (
        verify_signature(raw=b"{}", signature="deadbeef", secret="x")
        is False
    )


def test_subscription_status_mapping():
    from app.services.billing_service import status_for_event

    assert status_for_event("subscription_created") == "active"
    assert status_for_event("subscription_resumed") == "active"
    assert status_for_event("subscription_updated") == "active"
    assert status_for_event("subscription_cancelled") == "cancelled"
    assert status_for_event("subscription_paused") == "past_due"
