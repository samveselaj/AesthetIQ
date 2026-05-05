"""Unauthenticated onboarding — provisions org, admin user, location, FAQs,
booking routes, and default automations in a single call.

For the MVP this is open. In production lock this behind a signup gate or
admin-only endpoint.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core.deps import DbSession
from app.core.security import hash_password
from app.models.automation import AutomationRule, MessageTemplate
from app.models.booking_route import BookingRoute
from app.models.escalation import EscalationRule
from app.models.faq import FAQEntry
from app.models.location import Location
from app.models.organization import Organization, OrgSettings
from app.models.signup_token import SignupToken
from app.models.user import User, UserRole
from app.schemas.onboarding import OnboardingRequest
from app.services.treatment_normalizer import slugify_treatment_key

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


@router.post("", status_code=status.HTTP_201_CREATED)
def onboard(
    payload: OnboardingRequest,
    db: DbSession,
    token: str = Query(..., min_length=8, max_length=64),
) -> dict:
    now = datetime.now(timezone.utc)
    tok = db.execute(
        select(SignupToken).where(SignupToken.token == token)
    ).scalar_one_or_none()
    if not tok or tok.used_at is not None or tok.expires_at < now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired signup token")

    existing = db.execute(
        select(Organization).where(Organization.slug == payload.org_slug)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Slug already in use")

    org = Organization(
        name=payload.org_name,
        slug=payload.org_slug,
        subscription_status="active",
        lemon_subscription_id=tok.lemon_subscription_id,
    )
    db.add(org)
    db.flush()

    loc = Location(
        organization_id=org.id,
        name=payload.location_name,
        timezone=payload.location_timezone,
    )
    db.add(loc)
    db.flush()

    settings = OrgSettings(
        organization_id=org.id,
        brand_name=payload.org_name,
        default_location_id=loc.id,
        tone_of_voice=(
            "Warm, concise, professional, premium-but-approachable. Never robotic, "
            "never aggressive, never clinical advice."
        ),
        disclaimers=(
            "Messages are assistive and non-diagnostic. For medical concerns or "
            "possible side effects, we will connect you with our team."
        ),
        escalation_message=(
            "Thanks for your message. I'm flagging this for our team now so they "
            "can help you directly as soon as possible."
        ),
        booking_cta_style="soft",
        ai_enabled=True,
        auto_send_replies=True,
    )
    db.add(settings)

    admin = User(
        organization_id=org.id,
        full_name=payload.admin_name,
        email=str(payload.admin_email),
        password_hash=hash_password(payload.admin_password),
        role=UserRole.SPA_ADMIN.value,
        is_active=True,
    )
    db.add(admin)

    if payload.escalation_email:
        db.add(
            EscalationRule(
                organization_id=org.id,
                name="Default — medical and complaints",
                trigger_type="medical",
                conditions=None,
                notify_email=str(payload.escalation_email),
                is_active=True,
            )
        )

    for f in payload.faqs:
        db.add(
            FAQEntry(
                organization_id=org.id,
                category=f.category,
                question=f.question,
                answer=f.answer,
                is_active=True,
            )
        )

    for r in payload.booking_routes:
        db.add(
            BookingRoute(
                organization_id=org.id,
                location_id=loc.id,
                treatment_name=r.treatment_name,
                normalized_treatment_key=r.normalized_treatment_key
                or slugify_treatment_key(r.treatment_name),
                route_type=r.route_type,
                booking_url=r.booking_url,
                fallback_message=(
                    "Our team will reach out to help you book. Can you share a "
                    "good time to call you back?"
                ),
                is_active=True,
            )
        )

    # Default templates + automations
    _seed_default_templates_and_rules(db, org.id)

    tok.used_at = now
    db.add(tok)

    db.commit()
    return {"organization_id": str(org.id), "location_id": str(loc.id), "admin_id": str(admin.id)}


def _seed_default_templates_and_rules(db, organization_id) -> None:
    templates = {
        "welcome": "Thanks for reaching out! What treatment are you interested in?",
        "no_reply_24h": "Just checking in — would you like me to send the booking link for your consultation?",
        "no_booking_48h": "We still have availability this week if you'd like to schedule.",
        "no_reply_7d": "If you'd prefer, our team can text or call you directly. Just let me know a good time.",
        "missed_call_text": (
            "Sorry we missed your call. I can help with treatment questions, "
            "pricing, availability, or booking. What are you interested in?"
        ),
    }
    id_by_type = {}
    for kind, content in templates.items():
        t = MessageTemplate(
            organization_id=organization_id,
            name=kind.replace("_", " ").title(),
            template_type=kind,
            content=content,
            is_active=True,
        )
        db.add(t)
        db.flush()
        id_by_type[kind] = t.id

    for trigger, delay, template_type in (
        ("no_reply_24h", 24 * 60, "no_reply_24h"),
        ("no_booking_48h", 72 * 60, "no_booking_48h"),
        ("no_reply_7d", 7 * 24 * 60, "no_reply_7d"),
        ("missed_call", 0, "missed_call_text"),
    ):
        db.add(
            AutomationRule(
                organization_id=organization_id,
                name=f"Default {trigger}",
                trigger_event=trigger,
                channel_type="sms",
                is_active=True,
                delay_minutes=delay,
                template_id=id_by_type.get(template_type),
            )
        )
