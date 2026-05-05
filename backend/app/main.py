from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import (
    ai,
    auth,
    billing,
    booking_routes,
    conversations,
    dashboard,
    faqs,
    leads,
    onboarding,
    settings as settings_routes,
    users,
    webhooks,
)
from app.core.config import get_settings
from app.core.deps import require_active_subscription
from app.core.logging import configure_logging

configure_logging()
settings = get_settings()

_problems = settings.validate_production()
if _problems:
    raise RuntimeError(
        "Refusing to start in production with config problems:\n  - "
        + "\n  - ".join(_problems)
    )

app = FastAPI(
    title="MedSpa Lead Response + Booking Assistant",
    version="0.1.0",
    description="Respond to inbound med spa leads, qualify, hand off to booking, and escalate.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
def health() -> dict:
    """Lightweight health: stub mode reports 'ok' for that component;
    live mode performs a tiny network probe.
    """
    components = {
        "twilio": _twilio_health(),
        "openai": _openai_health(),
    }
    overall = "ok" if all(v == "ok" for v in components.values()) else "degraded"
    return {"status": overall, "components": components}


def _twilio_health() -> str:
    if not settings.twilio_live:
        return "ok"
    try:
        from twilio.rest import Client

        Client(settings.twilio_account_sid, settings.twilio_auth_token).api.accounts(
            settings.twilio_account_sid
        ).fetch()
        return "ok"
    except Exception:
        return "degraded"


def _openai_health() -> str:
    if not settings.openai_live:
        return "ok"
    if not settings.openai_api_key:
        return "degraded"
    return "ok"


API_PREFIX = "/api/v1"

# Ungated (always reachable)
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(onboarding.router, prefix=API_PREFIX)
app.include_router(webhooks.router, prefix=API_PREFIX)
app.include_router(billing.router, prefix=API_PREFIX)

# Gated by active subscription
GATED = [Depends(require_active_subscription)]
app.include_router(dashboard.router, prefix=API_PREFIX, dependencies=GATED)
app.include_router(leads.router, prefix=API_PREFIX, dependencies=GATED)
app.include_router(conversations.router, prefix=API_PREFIX, dependencies=GATED)
app.include_router(faqs.router, prefix=API_PREFIX, dependencies=GATED)
app.include_router(booking_routes.router, prefix=API_PREFIX, dependencies=GATED)
app.include_router(settings_routes.router, prefix=API_PREFIX, dependencies=GATED)
app.include_router(users.router, prefix=API_PREFIX, dependencies=GATED)
app.include_router(ai.router, prefix=API_PREFIX, dependencies=GATED)
