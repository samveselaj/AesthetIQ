from app.services.lead_service import normalize_phone


def test_normalize_phone_us_10_digits():
    assert normalize_phone("555-123-4567") == "+15551234567"


def test_normalize_phone_keeps_plus():
    assert normalize_phone("+44 20 7946 0000") == "+442079460000"


def test_normalize_phone_11_digits_us():
    assert normalize_phone("15551234567") == "+15551234567"


def test_normalize_phone_none():
    assert normalize_phone(None) is None
    assert normalize_phone("") is None
    assert normalize_phone("   ") is None
