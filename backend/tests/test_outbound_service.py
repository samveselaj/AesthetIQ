"""Smoke test that outbound_service.send_outbound is the canonical helper
and that message_service / followup_service / webhooks all import it from
the same place."""

import importlib


def test_send_outbound_lives_in_outbound_service():
    mod = importlib.import_module("app.services.outbound_service")
    assert hasattr(mod, "send_outbound"), "outbound_service must export send_outbound"


def test_message_service_imports_from_outbound_service():
    msg_src = (
        importlib.import_module("app.services.message_service").__file__
    )
    with open(msg_src, "r", encoding="utf-8") as f:
        body = f.read()
    assert "from app.services.outbound_service import send_outbound" in body
    assert "def _send_outbound" not in body


def test_followup_service_imports_from_outbound_service():
    f_src = importlib.import_module("app.services.followup_service").__file__
    with open(f_src, "r", encoding="utf-8") as f:
        body = f.read()
    assert "from app.services.outbound_service import send_outbound" in body
    assert "from app.services.message_service import _send_outbound" not in body
