from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.booking_route import BookingRoute
from app.schemas.booking_route import BookingRouteCreate, BookingRouteOut, BookingRouteUpdate
from app.services.treatment_normalizer import slugify_treatment_key

router = APIRouter(prefix="/booking-routes", tags=["booking-routes"])


@router.get("", response_model=list[BookingRouteOut])
def list_routes(db: DbSession, user: CurrentUser) -> list[BookingRouteOut]:
    rows = db.execute(
        select(BookingRoute)
        .where(BookingRoute.organization_id == user.organization_id)
        .order_by(BookingRoute.treatment_name.asc())
    ).scalars().all()
    return [BookingRouteOut.model_validate(r) for r in rows]


@router.post("", response_model=BookingRouteOut, status_code=status.HTTP_201_CREATED)
def create_route(payload: BookingRouteCreate, db: DbSession, user: CurrentUser) -> BookingRouteOut:
    data = payload.model_dump(exclude_none=True)
    data["normalized_treatment_key"] = (
        payload.normalized_treatment_key or slugify_treatment_key(payload.treatment_name)
    )
    if not data.get("fallback_message"):
        data["fallback_message"] = (
            "Our team will reach out to help you book. Can you share a good time "
            "to call you back?"
        )
    row = BookingRoute(organization_id=user.organization_id, **data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return BookingRouteOut.model_validate(row)


@router.patch("/{route_id}", response_model=BookingRouteOut)
def update_route(
    route_id: UUID,
    payload: BookingRouteUpdate,
    db: DbSession,
    user: CurrentUser,
) -> BookingRouteOut:
    row = db.get(BookingRoute, route_id)
    if not row or row.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking route not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.add(row)
    db.commit()
    db.refresh(row)
    return BookingRouteOut.model_validate(row)


@router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_route(route_id: UUID, db: DbSession, user: CurrentUser) -> Response:
    row = db.get(BookingRoute, route_id)
    if not row or row.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking route not found")
    db.delete(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
