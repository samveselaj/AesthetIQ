"""Conversation.ai_mode is a derived view of AI state used by the UI.
Pure-Python — no DB needed."""

from types import SimpleNamespace

from app.models.conversation import Conversation


def _mode(ai_enabled: bool, escalation_state: str) -> str:
    # Invoke the @property's getter on a plain stand-in so we don't have to
    # instantiate a real SQLAlchemy-instrumented row.
    return Conversation.ai_mode.fget(
        SimpleNamespace(ai_enabled=ai_enabled, escalation_state=escalation_state)
    )


def test_ai_mode_active():
    assert _mode(True, "none") == "active"


def test_ai_mode_paused():
    assert _mode(False, "none") == "paused"
    assert _mode(False, "resolved") == "paused"


def test_ai_mode_escalated_overrides_paused():
    # An escalated conversation surfaces as "escalated" even though ai_enabled is False.
    assert _mode(False, "escalated") == "escalated"
    assert _mode(True, "escalated") == "escalated"
