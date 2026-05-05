"""Subscription gate: routes that require an active org should 402 when
the org is past_due / cancelled / delinquent."""

import pytest
from fastapi import HTTPException


def test_require_active_subscription_passes_for_active(monkeypatch):
    from app.core import deps

    class FakeOrg:
        subscription_status = "active"

    class FakeDb:
        def get(self, _model, _id):
            return FakeOrg()

    class FakeUser:
        organization_id = "x"

    out = deps.require_active_subscription(user=FakeUser(), db=FakeDb())  # type: ignore[arg-type]
    assert out is True


def test_require_active_subscription_blocks_past_due():
    from app.core import deps

    class FakeOrg:
        subscription_status = "past_due"

    class FakeDb:
        def get(self, _model, _id):
            return FakeOrg()

    class FakeUser:
        organization_id = "x"

    with pytest.raises(HTTPException) as exc:
        deps.require_active_subscription(user=FakeUser(), db=FakeDb())  # type: ignore[arg-type]
    assert exc.value.status_code == 402
