import pytest
from pydantic import ValidationError

from app.schemas.ai import ClassificationResult, DraftResult, ExtractionResult


def test_classification_defaults_are_safe():
    c = ClassificationResult()
    assert c.intent == "unknown"
    assert c.needs_escalation is False
    assert 0.0 <= c.confidence <= 1.0


def test_classification_rejects_bad_intent():
    with pytest.raises(ValidationError):
        ClassificationResult(intent="marketing_hype")  # not in the Literal


def test_classification_rejects_bad_confidence():
    with pytest.raises(ValidationError):
        ClassificationResult(confidence=1.5)


def test_extraction_accepts_nulls():
    e = ExtractionResult()
    assert e.email is None and e.phone is None


def test_draft_requires_nonempty_reply():
    with pytest.raises(ValidationError):
        DraftResult(reply_text="")


def test_draft_limits_length():
    long_text = "x" * 2001
    with pytest.raises(ValidationError):
        DraftResult(reply_text=long_text)


def test_draft_roundtrip_ok():
    d = DraftResult(reply_text="Hi there", should_send_booking_link=True, booking_route_key="botox")
    data = d.model_dump()
    assert DraftResult.model_validate(data) == d
