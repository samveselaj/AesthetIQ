"""Given an inferred treatment + location, resolve the best next step:
- direct booking URL (if exact active route has one)
- consult URL for the treatment category
- callback / fallback message otherwise
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.booking_route import BookingRoute


@dataclass(frozen=True)
class BookingResolution:
    route: Optional[BookingRoute]
    url: Optional[str]
    is_callback: bool
    message: str


GENERIC_FALLBACK = (
    "Our team will reach out to help you book. Can you share a good time "
    "to call you back?"
)


def resolve_booking(
    db: Session,
    organization_id: UUID,
    treatment_key: Optional[str],
    location_id: Optional[UUID] = None,
) -> BookingResolution:
    """Match the best active BookingRoute for this org + treatment + location.

    Precedence:
    1. active exact-key route at this location
    2. active exact-key route with no location (org-wide)
    3. active general consultation route
    4. callback fallback
    """
    if not treatment_key:
        return _consultation_or_callback(db, organization_id, location_id)

    candidates = db.execute(
        select(BookingRoute)
        .where(BookingRoute.organization_id == organization_id)
        .where(BookingRoute.is_active.is_(True))
        .where(BookingRoute.normalized_treatment_key == treatment_key)
    ).scalars().all()

    if not candidates:
        return _consultation_or_callback(db, organization_id, location_id)

    def score(r: BookingRoute) -> tuple[int, int]:
        # prefer matching location, then routes that have a real URL over callbacks
        loc = 1 if (location_id and r.location_id == location_id) else 0
        has_url = 1 if r.booking_url else 0
        return (loc, has_url)

    best = sorted(candidates, key=score, reverse=True)[0]
    return _to_resolution(best)


def _consultation_or_callback(
    db: Session,
    organization_id: UUID,
    location_id: Optional[UUID],
) -> BookingResolution:
    consult = db.execute(
        select(BookingRoute)
        .where(BookingRoute.organization_id == organization_id)
        .where(BookingRoute.is_active.is_(True))
        .where(BookingRoute.normalized_treatment_key == "consultation_general")
    ).scalars().first()
    if consult:
        return _to_resolution(consult)

    return BookingResolution(
        route=None,
        url=None,
        is_callback=True,
        message=GENERIC_FALLBACK,
    )


def _to_resolution(route: BookingRoute) -> BookingResolution:
    if route.booking_url:
        return BookingResolution(
            route=route,
            url=route.booking_url,
            is_callback=route.route_type == "callback",
            message=(
                f"I can send you the booking link for {route.treatment_name} "
                f"if you'd like."
            ),
        )
    return BookingResolution(
        route=route,
        url=None,
        is_callback=True,
        message=route.fallback_message or GENERIC_FALLBACK,
    )
