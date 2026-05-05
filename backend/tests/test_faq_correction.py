"""Improve-this-reply creates a FAQEntry from the prior inbound and a staff
correction, with priority bumped to sort first."""

import pytest


def test_improve_reply_endpoint_exists():
    import importlib

    mod = importlib.import_module("app.api.v1.conversations")
    routes = [r.path for r in mod.router.routes]
    assert any(
        "/improve-reply" in p for p in routes
    ), f"expected improve-reply route, got {routes}"
