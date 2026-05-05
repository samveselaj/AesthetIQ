"""Seed three demo med-spa organizations with realistic, varied data so the app
feels like an active SaaS with paying customers.

Orgs created:
  1. Glow Aesthetics Miami        (slug: glow-aesthetics)
  2. Luxe Skin Studio Dallas      (slug: luxe-skin-dallas)        2 locations
  3. Sculpt Med Spa Scottsdale    (slug: sculpt-scottsdale)

Each org gets:
  - locations + business hours
  - 2-4 users (owner + staff)
  - tailored OrgSettings (different tone / cta style)
  - ~10 FAQs, 5-7 booking routes, 3-4 escalation rules
  - 6 message templates, 4-5 automation rules
  - ~40 leads (mixed status / source / treatment), with conversations,
    audit logs, AI logs, and pending follow-up jobs

Idempotent: re-running clears each demo org by slug before re-inserting.
Reproducible: uses a fixed random seed.

Usage:
    python seed.py              # default 3-org demo
    python seed.py --small      # original single-org behaviour (3 leads)
"""

from __future__ import annotations

import argparse
import random
import sys
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    AuditLog,
    AutomationRule,
    BookingRoute,
    BusinessHours,
    Conversation,
    EscalationRule,
    FAQEntry,
    Lead,
    Location,
    Message,
    MessageTemplate,
    Organization,
    OrgSettings,
    ScheduledJob,
    User,
    UserRole,
    WebhookEvent,
)
from app.models.ai_log import AIInteractionLog
from app.services.treatment_normalizer import slugify_treatment_key


RNG_SEED = 42
DEMO_PASSWORD = "demo1234"

ALL_DEMO_SLUGS = ("glow-aesthetics", "luxe-skin-dallas", "sculpt-scottsdale")


# ─────────────────────────────────────────────────────────────────────────────
# Reset
# ─────────────────────────────────────────────────────────────────────────────


def reset_demo(db, slugs: tuple[str, ...]) -> None:
    for slug in slugs:
        org = db.execute(
            select(Organization).where(Organization.slug == slug)
        ).scalar_one_or_none()
        if not org:
            continue
        org_id = org.id
        for model in (
            Message,
            Conversation,
            ScheduledJob,
            AuditLog,
            AIInteractionLog,
            WebhookEvent,
            FAQEntry,
            BookingRoute,
            EscalationRule,
            AutomationRule,
            MessageTemplate,
            BusinessHours,
            Lead,
            Location,
            OrgSettings,
            User,
        ):
            db.execute(delete(model).where(model.organization_id == org_id))
        db.execute(delete(Organization).where(Organization.id == org_id))
    db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Org specs
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class StaffSpec:
    full_name: str
    email: str
    role: str = UserRole.STAFF.value


@dataclass
class LocationSpec:
    name: str
    phone_number: str
    email: str
    address: str
    timezone: str


@dataclass
class OrgSpec:
    slug: str
    name: str
    brand_name: str
    tone: str
    cta_style: str  # soft | aggressive
    auto_send_replies: bool
    locations: list[LocationSpec]
    users: list[StaffSpec]
    escalation_email: str
    front_desk_email: str
    lead_count: int = 40


def _org_specs() -> list[OrgSpec]:
    return [
        OrgSpec(
            slug="glow-aesthetics",
            name="Glow Aesthetics",
            brand_name="Glow Aesthetics",
            tone=(
                "Warm, concise, professional, premium-but-approachable. Never "
                "robotic, never aggressive, never clinical advice."
            ),
            cta_style="soft",
            auto_send_replies=False,
            locations=[
                LocationSpec(
                    "Glow Aesthetics Miami",
                    "+13055550101",
                    "hello@glowaesthetics.demo",
                    "123 Ocean Dr, Miami Beach, FL 33139",
                    "America/New_York",
                ),
            ],
            users=[
                StaffSpec("Dana Owner", "owner@glowaesthetics.demo", UserRole.SPA_ADMIN.value),
                StaffSpec("Mia Coordinator", "front@glowaesthetics.demo"),
                StaffSpec("Alex Reception", "alex@glowaesthetics.demo"),
            ],
            escalation_email="owner@glowaesthetics.demo",
            front_desk_email="front@glowaesthetics.demo",
            lead_count=42,
        ),
        OrgSpec(
            slug="luxe-skin-dallas",
            name="Luxe Skin Studio",
            brand_name="Luxe Skin Studio Dallas",
            tone=(
                "Polished, refined, conservative. Educate first, sell second. "
                "Avoid hype words; always offer a consultation."
            ),
            cta_style="soft",
            auto_send_replies=True,
            locations=[
                LocationSpec(
                    "Luxe Skin Uptown",
                    "+12145550102",
                    "uptown@luxeskindallas.demo",
                    "2200 Cedar Springs Rd, Dallas, TX 75201",
                    "America/Chicago",
                ),
                LocationSpec(
                    "Luxe Skin Plano",
                    "+12145550103",
                    "plano@luxeskindallas.demo",
                    "5000 Preston Rd, Plano, TX 75093",
                    "America/Chicago",
                ),
            ],
            users=[
                StaffSpec("Priya Patel", "owner@luxeskindallas.demo", UserRole.SPA_ADMIN.value),
                StaffSpec("Jordan Hayes", "jordan@luxeskindallas.demo"),
                StaffSpec("Sam Reyes", "sam@luxeskindallas.demo"),
            ],
            escalation_email="owner@luxeskindallas.demo",
            front_desk_email="jordan@luxeskindallas.demo",
            lead_count=44,
        ),
        OrgSpec(
            slug="sculpt-scottsdale",
            name="Sculpt Med Spa",
            brand_name="Sculpt Med Spa Scottsdale",
            tone=(
                "Confident, energetic, results-oriented. Mention financing and "
                "package savings when relevant. Always close with a clear next step."
            ),
            cta_style="aggressive",
            auto_send_replies=True,
            locations=[
                LocationSpec(
                    "Sculpt Scottsdale",
                    "+14805550104",
                    "hello@sculptmedspa.demo",
                    "7001 N Scottsdale Rd, Scottsdale, AZ 85253",
                    "America/Phoenix",
                ),
            ],
            users=[
                StaffSpec("Chase Morgan", "owner@sculptmedspa.demo", UserRole.SPA_ADMIN.value),
                StaffSpec("Riley Banks", "riley@sculptmedspa.demo"),
                StaffSpec("Taylor Quinn", "taylor@sculptmedspa.demo"),
                StaffSpec("Devon Cole", "devon@sculptmedspa.demo"),
            ],
            escalation_email="owner@sculptmedspa.demo",
            front_desk_email="riley@sculptmedspa.demo",
            lead_count=44,
        ),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Static content per-org (FAQs, booking routes, templates)
# ─────────────────────────────────────────────────────────────────────────────


def _faqs_for(spec: OrgSpec) -> list[dict]:
    base = [
        {"category": "pricing", "question": "How much does Botox cost?",
         "answer": "Botox is priced per unit and varies by the areas treated. Your exact plan is confirmed at consultation.",
         "tags": ["botox", "pricing"], "priority": 10},
        {"category": "treatment_info", "question": "How long does Botox last?",
         "answer": "Most patients enjoy results for roughly 3-4 months.",
         "tags": ["botox", "duration"]},
        {"category": "treatment_info", "question": "Is there downtime after dermal filler?",
         "answer": "Typically minimal — some swelling or bruising for 1-2 days is common.",
         "tags": ["filler", "downtime"]},
        {"category": "prep", "question": "How should I prep for laser hair removal?",
         "answer": "Avoid sun exposure for 2 weeks and shave (don't wax) the area 24 hours before your appointment.",
         "tags": ["laser", "prep"]},
        {"category": "treatment_info", "question": "How often should I get a HydraFacial?",
         "answer": "Most clients book a HydraFacial every 4-6 weeks for best results.",
         "tags": ["hydrafacial", "frequency"]},
        {"category": "process", "question": "Do I need a consultation first?",
         "answer": "Yes — new clients begin with a brief consultation so we can tailor a plan to your goals.",
         "tags": ["consultation"]},
        {"category": "pricing", "question": "Do you offer financing?",
         "answer": "Yes — we offer financing through Cherry and Afterpay for treatments and packages.",
         "tags": ["financing"]},
        {"category": "process", "question": "How do I reschedule my appointment?",
         "answer": "Our team will help reschedule you directly — I'll flag this for them right now.",
         "tags": ["reschedule"]},
    ]
    if spec.slug == "glow-aesthetics":
        base.extend([
            {"category": "logistics", "question": "What are your office hours?",
             "answer": "Mon-Fri 10am-6pm, Sat 10am-2pm, closed Sundays.", "tags": ["hours"]},
            {"category": "logistics", "question": "Where can I park?",
             "answer": "Free street parking on Ocean Dr or use the public garage at 300 Ocean Dr.", "tags": ["parking"]},
        ])
    elif spec.slug == "luxe-skin-dallas":
        base.extend([
            {"category": "logistics", "question": "Do both locations offer the same treatments?",
             "answer": "Most treatments are offered at both Uptown and Plano. Coolsculpting is currently Uptown only.",
             "tags": ["locations", "uptown", "plano"]},
            {"category": "treatment_info", "question": "Tell me about your microneedling.",
             "answer": "Our microneedling uses SkinPen with optional PRP. Expect 1-2 days of redness.",
             "tags": ["microneedling"]},
        ])
    elif spec.slug == "sculpt-scottsdale":
        base.extend([
            {"category": "treatment_info", "question": "How many CoolSculpting sessions do I need?",
             "answer": "Most clients see meaningful results in 1-3 sessions per area. Final plan is confirmed at consultation.",
             "tags": ["coolsculpting"]},
            {"category": "pricing", "question": "Do you offer treatment packages?",
             "answer": "Yes — Botox, filler and laser packages save up to 20%. Ask us about our membership.",
             "tags": ["packages", "pricing"]},
        ])
    return base


def _booking_routes_for(spec: OrgSpec) -> list[dict]:
    routes = [
        {"treatment_name": "Botox consultation", "normalized_treatment_key": "botox",
         "route_type": "consult", "booking_url": f"https://book.{spec.slug}.demo/botox-consult"},
        {"treatment_name": "Filler consultation", "normalized_treatment_key": "filler",
         "route_type": "consult", "booking_url": f"https://book.{spec.slug}.demo/filler-consult"},
        {"treatment_name": "Laser hair removal consultation", "normalized_treatment_key": "laser_hair_removal",
         "route_type": "consult", "booking_url": f"https://book.{spec.slug}.demo/lhr-consult"},
        {"treatment_name": "HydraFacial", "normalized_treatment_key": "hydrafacial",
         "route_type": "direct_booking", "booking_url": f"https://book.{spec.slug}.demo/hydrafacial"},
        {"treatment_name": "General consultation", "normalized_treatment_key": "consultation_general",
         "route_type": "consult", "booking_url": f"https://book.{spec.slug}.demo/consult"},
    ]
    if spec.slug == "luxe-skin-dallas":
        routes.append({
            "treatment_name": "Microneedling", "normalized_treatment_key": "microneedling",
            "route_type": "direct_booking", "booking_url": f"https://book.{spec.slug}.demo/microneedling",
        })
    if spec.slug == "sculpt-scottsdale":
        routes.append({
            "treatment_name": "CoolSculpting consultation", "normalized_treatment_key": "coolsculpting",
            "route_type": "consult", "booking_url": f"https://book.{spec.slug}.demo/coolsculpting",
        })
    return routes


def _templates_for(spec: OrgSpec) -> dict[str, str]:
    base_brand = spec.brand_name
    return {
        "welcome": f"Thanks for reaching out to {base_brand}. What treatment are you interested in?",
        "no_reply_24h": "Just checking in — would you like me to send the booking link for your consultation?",
        "no_booking_48h": "We still have availability this week if you'd like to schedule.",
        "no_reply_7d": "If you'd prefer, our team can text or call you directly. Just let me know a good time.",
        "missed_call_text": (
            f"Sorry we missed your call to {base_brand}. I can help with treatment "
            "questions, pricing, availability, or booking — what are you interested in?"
        ),
        "escalation_ack": (
            "Thanks for your message. I'm flagging this for our team now so they can "
            "help you directly as soon as possible."
        ),
        "booking_push": "I can send you the booking link for that consultation if you'd like.",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Lead / conversation generation
# ─────────────────────────────────────────────────────────────────────────────


FIRST_NAMES = [
    "Sasha", "Ryan", "Jordan", "Olivia", "Marcus", "Priya", "Hannah", "Diego",
    "Emma", "Tyler", "Chloe", "Mateo", "Ava", "Liam", "Sofia", "Noah",
    "Isabella", "Ethan", "Mia", "Aiden", "Charlotte", "Caleb", "Amelia",
    "Brooklyn", "Camila", "Daniel", "Elena", "Felix", "Gianna", "Henry",
    "Iris", "Jaylen", "Kai", "Layla", "Mason", "Nora", "Owen", "Penelope",
    "Quinn", "Riley", "Stella", "Theo", "Uma", "Vivian", "Wyatt", "Xander",
    "Yasmin", "Zoe", "Alex", "Blake", "Cameron", "Devon",
]
LAST_INITIALS = ["A.", "B.", "C.", "D.", "F.", "G.", "H.", "K.", "L.", "M.",
                 "N.", "P.", "R.", "S.", "T.", "V.", "W."]

TREATMENT_KEYS = [
    "botox", "filler", "laser_hair_removal", "hydrafacial",
    "consultation_general", "microneedling", "coolsculpting",
]
TREATMENT_WEIGHTS = [30, 22, 14, 14, 8, 6, 6]  # rough realistic mix

SOURCE_WEIGHTS = [("sms", 55), ("form", 30), ("missed_call", 15)]

# (status, weight)
LEAD_STATUS_WEIGHTS = [
    ("new", 22),
    ("contacted", 28),
    ("booked", 20),
    ("escalated", 10),
    ("closed_lost", 15),
    ("contacted", 5),  # bias slightly more "contacted" mid-funnel
]


# Conversation script library, keyed by an internal scenario id.
# Each is a list of (sender_type, content, ai_generated, gap_minutes)
SCRIPTS: dict[str, list[tuple]] = {
    "botox_pricing": [
        ("lead", "Hi! How much is Botox?", False, 0),
        ("ai", "Botox is priced per unit and varies by the areas treated. "
               "Your exact plan is confirmed at consultation. "
               "I can send the booking link if you'd like — {booking_url}", True, 2),
        ("lead", "Yes please send it", False, 35),
        ("ai", "Sent! Here's the link: {booking_url}. Looking forward to it.", True, 3),
    ],
    "filler_downtime": [
        ("lead", "How long is the recovery for lip filler?", False, 0),
        ("ai", "Most patients have minimal downtime — light swelling or "
               "bruising for 1-2 days is common. Want me to share our "
               "consultation link?", True, 4),
    ],
    "laser_prep": [
        ("lead", "Do I need to do anything before laser hair removal?", False, 0),
        ("ai", "Yes — avoid sun for 2 weeks and shave (don't wax) the area "
               "24 hours before. Want me to send the booking link?", True, 5),
        ("lead", "Sure", False, 10),
        ("ai", "Here you go: {booking_url}", True, 1),
    ],
    "hydrafacial_book": [
        ("lead", "I'd like to book a HydraFacial.", False, 0),
        ("ai", "Great — here's our HydraFacial booking link: {booking_url}", True, 1),
    ],
    "reschedule": [
        ("lead", "I need to move my appointment Thursday to next week.", False, 0),
        ("ai", "Thanks — I'm flagging this for our team so they can move that for you.", True, 2),
        ("staff", "Hi! I see Thursday 2pm. I have Tuesday 11am or Wednesday 4pm next week — which works?", False, 28),
        ("lead", "Wednesday 4pm please", False, 90),
        ("staff", "Booked you for Wed 4pm — see you then!", False, 4),
    ],
    "complaint": [
        ("lead", "I had laser yesterday and the technician was rude to me. "
                "I'm extremely unhappy.", False, 0),
        ("ai", "I'm so sorry to hear that. I'm flagging this for our team "
               "right away so they can make it right.", True, 1),
        ("staff", "This is Dana, the owner. I'm so sorry — can I call you "
                  "today to make this right?", False, 35),
    ],
    "medical_swelling": [
        ("lead", "I got filler 2 days ago and my lip is very swollen and bruised. "
                 "Is that normal?", False, 0),
        ("ai", "Thanks for letting us know — I'm flagging this for our team "
               "right now so they can help you directly.", True, 1),
    ],
    "stop_optout": [
        ("lead", "Stop texting me", False, 0),
        ("ai", "You've been opted out and won't receive further messages. "
               "Reply START at any time to resume.", True, 1),
    ],
    "human_request": [
        ("lead", "Can I please talk to a human?", False, 0),
        ("ai", "Of course — I'm flagging this for our team so a person can "
               "follow up with you directly.", True, 1),
        ("staff", "Hi, this is Mia from the front desk. How can I help?", False, 12),
    ],
    "consult_general": [
        ("lead", "I'm interested in something for fine lines around my eyes.", False, 0),
        ("ai", "We can absolutely help. The right next step is a quick "
               "consultation — would you like me to send the booking link?", True, 3),
        ("lead", "Sure", False, 8),
        ("ai", "Here you go: {booking_url}", True, 1),
    ],
    "missed_call": [
        ("ai", "Sorry we missed your call. I can help with treatment "
               "questions, pricing, availability, or booking — what are "
               "you interested in?", True, 0),
    ],
    "missed_call_recovered": [
        ("ai", "Sorry we missed your call. I can help with treatment "
               "questions, pricing, availability, or booking — what are "
               "you interested in?", True, 0),
        ("lead", "Hi yes I wanted to ask about Botox pricing", False, 12),
        ("ai", "Botox is priced per unit and varies by the areas treated. "
               "Want me to send the consultation link? {booking_url}", True, 2),
        ("lead", "Yes please", False, 6),
        ("ai", "Here you go: {booking_url}", True, 1),
    ],
    "form_dropoff": [
        ("lead", "Hi, I filled out the form on your website. I'd like to "
                 "know about CoolSculpting.", False, 0),
        ("ai", "Thanks for reaching out! CoolSculpting is one of our most "
               "popular treatments. Would you like me to send the consultation "
               "link? {booking_url}", True, 4),
    ],
    "ghosted": [
        ("lead", "Hi, what's the price for filler?", False, 0),
        ("ai", "Filler pricing depends on the areas and product chosen. "
               "Want me to send the consultation link? {booking_url}", True, 3),
    ],
    "insurance": [
        ("lead", "Do you take insurance?", False, 0),
        ("ai", "Most aesthetic treatments aren't covered by insurance, but "
               "we offer Cherry and Afterpay financing. Want details?", True, 2),
        ("lead", "ok thanks", False, 14),
    ],
    "gift_card": [
        ("lead", "Do you sell gift cards?", False, 0),
        ("ai", "Yes! Gift cards are available in any amount — I can have "
               "the team text you a link if you'd like.", True, 2),
        ("lead", "Yes please", False, 8),
        ("staff", "Just sent — let me know if you don't see it!", False, 6),
    ],
    "package_question": [
        ("lead", "Do you offer Botox packages?", False, 0),
        ("ai", "Yes — our packages save up to 20% versus per-visit pricing. "
               "Want me to send the consultation link? {booking_url}", True, 3),
        ("lead", "Yes!", False, 22),
        ("ai", "Here you go: {booking_url}", True, 1),
    ],
}


# ─────────────────────────────────────────────────────────────────────────────
# Seeding
# ─────────────────────────────────────────────────────────────────────────────


def seed_demo() -> None:
    rng = random.Random(RNG_SEED)
    db = SessionLocal()
    try:
        reset_demo(db, ALL_DEMO_SLUGS)
        for spec in _org_specs():
            _seed_org(db, spec, rng)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print("Demo seed complete. Logins:")
    print("  Glow Aesthetics:   owner@glowaesthetics.demo / demo1234")
    print("  Luxe Skin Dallas:  owner@luxeskindallas.demo / demo1234")
    print("  Sculpt Scottsdale: owner@sculptmedspa.demo / demo1234")


def _seed_org(db, spec: OrgSpec, rng: random.Random) -> None:
    org = Organization(name=spec.name, slug=spec.slug, subscription_status="active")
    db.add(org)
    db.flush()

    # Locations
    locations: list[Location] = []
    for loc_spec in spec.locations:
        loc = Location(
            organization_id=org.id,
            name=loc_spec.name,
            phone_number=loc_spec.phone_number,
            email=loc_spec.email,
            address=loc_spec.address,
            timezone=loc_spec.timezone,
        )
        db.add(loc)
        db.flush()
        locations.append(loc)

    default_loc = locations[0]

    # Settings
    db.add(OrgSettings(
        organization_id=org.id,
        brand_name=spec.brand_name,
        default_location_id=default_loc.id,
        tone_of_voice=spec.tone,
        disclaimers=(
            "Messages are assistive and non-diagnostic. For medical concerns "
            "or possible side effects, we will connect you with our team."
        ),
        escalation_message=(
            "Thanks for your message. I'm flagging this for our team now so "
            "they can help you directly as soon as possible."
        ),
        booking_cta_style=spec.cta_style,
        ai_enabled=True,
        auto_send_replies=spec.auto_send_replies,
    ))

    # Users
    users: list[User] = []
    for staff in spec.users:
        u = User(
            organization_id=org.id,
            full_name=staff.full_name,
            email=staff.email,
            password_hash=hash_password(DEMO_PASSWORD),
            role=staff.role,
        )
        db.add(u)
        db.flush()
        users.append(u)

    # Business hours per location
    for loc in locations:
        for dow in range(0, 5):
            db.add(BusinessHours(
                organization_id=org.id, location_id=loc.id, day_of_week=dow,
                open_time=time(10, 0), close_time=time(18, 0), is_closed=False,
            ))
        db.add(BusinessHours(
            organization_id=org.id, location_id=loc.id, day_of_week=5,
            open_time=time(10, 0), close_time=time(14, 0), is_closed=False,
        ))
        db.add(BusinessHours(
            organization_id=org.id, location_id=loc.id, day_of_week=6,
            open_time=None, close_time=None, is_closed=True,
        ))

    # FAQs
    for f in _faqs_for(spec):
        db.add(FAQEntry(organization_id=org.id, location_id=default_loc.id, **f))

    # Booking routes (one per route per default location)
    for r in _booking_routes_for(spec):
        key = r.get("normalized_treatment_key") or slugify_treatment_key(r["treatment_name"])
        db.add(BookingRoute(
            organization_id=org.id,
            location_id=default_loc.id,
            treatment_name=r["treatment_name"],
            normalized_treatment_key=key,
            route_type=r["route_type"],
            booking_url=r.get("booking_url"),
            fallback_message=(
                "Our team will reach out to help you book. Can you share a "
                "good time to call you back?"
            ),
            is_active=True,
        ))

    # Escalation rules
    db.add(EscalationRule(
        organization_id=org.id, name="Medical concerns → owner",
        trigger_type="medical", notify_email=spec.escalation_email, is_active=True,
    ))
    db.add(EscalationRule(
        organization_id=org.id, name="Complaints → owner",
        trigger_type="complaint", notify_email=spec.escalation_email, is_active=True,
    ))
    db.add(EscalationRule(
        organization_id=org.id, name="Existing appointment changes",
        trigger_type="existing_client_issue", notify_email=spec.front_desk_email, is_active=True,
    ))
    db.add(EscalationRule(
        organization_id=org.id, name="Human handoff requests",
        trigger_type="human_request", notify_email=spec.front_desk_email, is_active=True,
    ))

    # Templates
    template_ids: dict[str, UUID] = {}
    for kind, content in _templates_for(spec).items():
        t = MessageTemplate(
            organization_id=org.id, name=kind.replace("_", " ").title(),
            template_type=kind, content=content, is_active=True,
        )
        db.add(t)
        db.flush()
        template_ids[kind] = t.id

    # Automation rules
    for trigger, delay, template_type in (
        ("new_lead", 0, "welcome"),
        ("no_reply_24h", 24 * 60, "no_reply_24h"),
        ("no_booking_48h", 72 * 60, "no_booking_48h"),
        ("no_reply_7d", 7 * 24 * 60, "no_reply_7d"),
        ("missed_call", 0, "missed_call_text"),
    ):
        db.add(AutomationRule(
            organization_id=org.id,
            name=f"Default {trigger}",
            trigger_event=trigger,
            channel_type="sms",
            is_active=True,
            delay_minutes=delay,
            template_id=template_ids.get(template_type),
        ))

    # Booking routes by key, for filling {booking_url} into scripts
    routes_by_key = {
        r["normalized_treatment_key"]: r["booking_url"]
        for r in _booking_routes_for(spec)
    }

    # Leads + conversations
    _seed_leads_and_conversations(
        db,
        org_id=org.id,
        locations=locations,
        users=users,
        routes_by_key=routes_by_key,
        spec=spec,
        rng=rng,
    )


def _seed_leads_and_conversations(
    db,
    *,
    org_id: UUID,
    locations: list[Location],
    users: list[User],
    routes_by_key: dict,
    spec: OrgSpec,
    rng: random.Random,
) -> None:
    now = datetime.now(timezone.utc)

    used_phones: set[str] = set()
    used_emails: set[str] = set()

    for i in range(spec.lead_count):
        location = rng.choice(locations)
        source = _weighted(rng, SOURCE_WEIGHTS)
        treatment = _weighted_list(rng, TREATMENT_KEYS, TREATMENT_WEIGHTS)
        status, scenario = _pick_status_and_scenario(rng, source, treatment, i)

        first = rng.choice(FIRST_NAMES)
        last_initial = rng.choice(LAST_INITIALS)
        full = f"{first} {last_initial}"
        phone = _unique_phone(rng, used_phones)
        email = _unique_email(rng, first, last_initial, used_emails) if source == "form" or rng.random() < 0.4 else None

        # opted-out leads (rare)
        do_not_contact = scenario == "stop_optout"

        # timestamps
        days_ago = rng.randint(0, 28)
        base_time = now - timedelta(days=days_ago, hours=rng.randint(0, 23), minutes=rng.randint(0, 59))

        booking_status = "not_sent"
        if status == "booked":
            booking_status = "booked"
        elif status in ("contacted", "escalated"):
            booking_status = rng.choice(["link_sent", "not_sent"])

        lifecycle = {
            "new": "inquiry",
            "contacted": "engaged",
            "booked": "qualified",
            "escalated": "engaged",
            "closed_lost": "engaged",
        }[status]

        assigned_to = None
        if status in ("escalated", "booked", "contacted") and rng.random() < 0.5:
            assigned_to = rng.choice(users).id

        lead = Lead(
            organization_id=org_id,
            location_id=location.id,
            source_type=source,
            source_label={
                "sms": "twilio_sms",
                "form": "website_contact_form",
                "missed_call": "twilio_voice",
            }[source],
            first_name=first,
            last_name=last_initial.rstrip("."),
            full_name=full,
            phone=phone,
            email=email,
            treatment_interest=treatment if treatment != "consultation_general" else None,
            preferred_contact_method="sms" if source != "form" else "email",
            status=status,
            lifecycle_stage=lifecycle,
            booking_status=booking_status,
            do_not_contact=do_not_contact,
            assigned_to_user_id=assigned_to,
            notes=_lead_note(rng, status, scenario),
            created_at=base_time,
            updated_at=base_time,
        )
        db.add(lead)
        db.flush()

        # Conversation + messages
        conv_status, ai_enabled, escalation_state = _conversation_state(status, scenario)
        channel_type = "sms" if source != "form" else "sms"  # all conversations live in SMS thread
        conv = Conversation(
            organization_id=org_id, lead_id=lead.id,
            channel_type=channel_type, status=conv_status,
            ai_enabled=ai_enabled, escalation_state=escalation_state,
            created_at=base_time,
            updated_at=base_time,
        )
        db.add(conv)
        db.flush()

        booking_url = routes_by_key.get(treatment) or routes_by_key.get("consultation_general") \
            or "https://example.com/book"

        last_inbound = None
        last_outbound = None
        cursor = base_time
        script = SCRIPTS[scenario]
        for sender_type, content, ai_generated, gap_minutes in script:
            cursor = cursor + timedelta(minutes=gap_minutes)
            if cursor > now:
                cursor = now - timedelta(minutes=rng.randint(1, 5))
            direction = "inbound" if sender_type == "lead" else "outbound"
            text = content.replace("{booking_url}", booking_url)
            m = Message(
                organization_id=org_id,
                conversation_id=conv.id,
                lead_id=lead.id,
                direction=direction,
                sender_type=sender_type,
                channel_type="sms",
                content=text,
                delivery_status="delivered" if direction == "outbound" else "received",
                ai_generated=ai_generated,
                reviewed_by_human=(sender_type == "staff"),
            )
            m.created_at = cursor
            db.add(m)
            if direction == "inbound":
                last_inbound = cursor
            else:
                last_outbound = cursor

            # AI interaction logs for AI-generated messages
            if ai_generated:
                db.add(AIInteractionLog(
                    organization_id=org_id,
                    conversation_id=conv.id,
                    lead_id=lead.id,
                    task_type="draft_reply",
                    input_text=script[0][1] if script[0][0] == "lead" else "(missed call)",
                    output_json={"reply": text[:280], "treatment_key": treatment},
                    prompt_version="v1",
                    model_name="gpt-4o-mini-stub",
                    success=True,
                ))

        lead.last_inbound_at = last_inbound
        lead.last_outbound_at = last_outbound
        # Bump updated_at to the most recent activity so windowed reports work.
        latest_activity = max(
            t for t in (last_inbound, last_outbound, base_time) if t is not None
        )
        lead.updated_at = latest_activity
        conv.updated_at = latest_activity

        # Audit log on lifecycle events
        if status == "escalated":
            db.add(AuditLog(
                organization_id=org_id,
                actor_type="system",
                action="escalate",
                entity_type="conversation",
                entity_id=conv.id,
                audit_metadata={"reason": _escalation_reason(scenario), "scenario": scenario},
            ))
        if do_not_contact:
            db.add(AuditLog(
                organization_id=org_id,
                actor_type="system",
                action="opt_out",
                entity_type="lead",
                entity_id=lead.id,
                audit_metadata={"channel": "sms"},
            ))
        if status == "booked":
            db.add(AuditLog(
                organization_id=org_id,
                actor_type="ai",
                action="booking_link_sent",
                entity_type="lead",
                entity_id=lead.id,
                audit_metadata={"treatment": treatment, "booking_url": booking_url},
            ))

        # Pending follow-up jobs for some new/contacted leads
        if status in ("new", "contacted") and not do_not_contact and rng.random() < 0.45:
            run_at = now + timedelta(hours=rng.choice([1, 6, 24, 48]))
            db.add(ScheduledJob(
                organization_id=org_id,
                lead_id=lead.id,
                conversation_id=conv.id,
                kind="follow_up_sms",
                run_at=run_at,
                status="pending",
            ))


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _weighted(rng: random.Random, pairs: list[tuple[str, int]]) -> str:
    items = [p[0] for p in pairs]
    weights = [p[1] for p in pairs]
    return rng.choices(items, weights=weights, k=1)[0]


def _weighted_list(rng: random.Random, items: list[str], weights: list[int]) -> str:
    return rng.choices(items, weights=weights, k=1)[0]


def _unique_phone(rng: random.Random, used: set[str]) -> str:
    while True:
        candidate = f"+1{rng.randint(2000000000, 9999999999)}"
        if candidate not in used:
            used.add(candidate)
            return candidate


def _unique_email(rng: random.Random, first: str, last_initial: str, used: set[str]) -> str:
    while True:
        suffix = rng.randint(1, 9999)
        candidate = f"{first.lower()}.{last_initial.rstrip('.').lower()}{suffix}@example.com"
        if candidate not in used:
            used.add(candidate)
            return candidate


def _pick_status_and_scenario(
    rng: random.Random, source: str, treatment: str, i: int,
) -> tuple[str, str]:
    """Pick a (status, scenario) tuple using realistic probabilities and source compatibility."""
    # Source-specific overrides
    if source == "missed_call":
        if rng.random() < 0.4:
            return ("contacted", "missed_call_recovered")
        return ("new", "missed_call")

    # Scenario buckets per status
    status = _weighted(rng, [
        ("new", 22), ("contacted", 30), ("booked", 20),
        ("escalated", 10), ("closed_lost", 18),
    ])

    if status == "escalated":
        scenario = rng.choice(["medical_swelling", "complaint", "human_request"])
        return (status, scenario)
    if status == "booked":
        scenario = rng.choice([
            "botox_pricing", "hydrafacial_book", "laser_prep",
            "consult_general", "package_question",
        ])
        return (status, scenario)
    if status == "closed_lost":
        # ghost or stop
        scenario = rng.choices(["ghosted", "stop_optout", "insurance"], weights=[60, 15, 25], k=1)[0]
        return (status, scenario)
    if status == "contacted":
        scenario = rng.choice([
            "filler_downtime", "package_question", "gift_card",
            "consult_general", "form_dropoff", "reschedule",
        ])
        return (status, scenario)
    # new
    scenario = rng.choice([
        "botox_pricing", "filler_downtime", "laser_prep",
        "hydrafacial_book", "consult_general", "form_dropoff", "ghosted",
    ])
    return (status, scenario)


def _conversation_state(status: str, scenario: str) -> tuple[str, bool, str]:
    if scenario in ("medical_swelling", "complaint", "human_request"):
        return ("waiting_on_staff", False, "escalated")
    if status == "booked":
        return ("closed", True, "none")
    if status == "closed_lost":
        return ("closed", True, "none")
    if status == "new":
        return ("open", True, "none")
    return ("waiting_on_lead", True, "none")


def _lead_note(rng: random.Random, status: str, scenario: str) -> Optional[str]:
    if scenario == "medical_swelling":
        return "Reported swelling 2 days post-filler. Owner notified."
    if scenario == "complaint":
        return "Service complaint — owner reached out personally."
    if status == "booked":
        return None
    if rng.random() < 0.2:
        return rng.choice([
            "Returning client — previous Botox in 2024.",
            "Found us via Instagram ad.",
            "Referred by existing client.",
            "Asked about Cherry financing.",
        ])
    return None


def _escalation_reason(scenario: str) -> str:
    return {
        "medical_swelling": "medical",
        "complaint": "complaint",
        "human_request": "human_request",
    }.get(scenario, "off_script")


# ─────────────────────────────────────────────────────────────────────────────
# Legacy small-mode (kept for fast-path dev)
# ─────────────────────────────────────────────────────────────────────────────


def seed_small() -> None:
    """Original 3-lead Glow-only seed, useful for quick dev iterations."""
    db = SessionLocal()
    try:
        reset_demo(db, ("glow-aesthetics",))
        spec = _org_specs()[0]
        spec.lead_count = 3
        rng = random.Random(RNG_SEED)
        _seed_org(db, spec, rng)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print("Small seed complete. Login: owner@glowaesthetics.demo / demo1234")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--small", action="store_true",
                        help="Seed only Glow Aesthetics with 3 sample leads (fast dev mode)")
    args = parser.parse_args()
    if args.small:
        seed_small()
    else:
        seed_demo()
