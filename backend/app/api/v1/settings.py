from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.location import Location
from app.models.organization import BusinessHours, OrgSettings
from app.schemas.settings import (
    BusinessHoursItem,
    BusinessHoursOut,
    LocationCreate,
    LocationOut,
    LocationUpdate,
    OrgSettingsOut,
    OrgSettingsUpdate,
)

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=OrgSettingsOut)
def get_settings_endpoint(db: DbSession, user: CurrentUser) -> OrgSettingsOut:
    row = db.execute(
        select(OrgSettings).where(OrgSettings.organization_id == user.organization_id)
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Settings not found")
    return OrgSettingsOut.model_validate(row)


@router.patch("", response_model=OrgSettingsOut)
def update_settings(
    payload: OrgSettingsUpdate, db: DbSession, user: CurrentUser
) -> OrgSettingsOut:
    row = db.execute(
        select(OrgSettings).where(OrgSettings.organization_id == user.organization_id)
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Settings not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.add(row)
    db.commit()
    db.refresh(row)
    return OrgSettingsOut.model_validate(row)


# ---------- Locations ----------


@router.get("/locations", response_model=list[LocationOut])
def list_locations(db: DbSession, user: CurrentUser) -> list[LocationOut]:
    rows = db.execute(
        select(Location)
        .where(Location.organization_id == user.organization_id)
        .order_by(Location.name.asc())
    ).scalars().all()
    return [LocationOut.model_validate(r) for r in rows]


@router.post("/locations", response_model=LocationOut, status_code=201)
def create_location(
    payload: LocationCreate, db: DbSession, user: CurrentUser
) -> LocationOut:
    row = Location(organization_id=user.organization_id, **payload.model_dump(exclude_none=True))
    db.add(row)
    db.commit()
    db.refresh(row)
    return LocationOut.model_validate(row)


@router.patch("/locations/{location_id}", response_model=LocationOut)
def update_location(
    location_id: UUID,
    payload: LocationUpdate,
    db: DbSession,
    user: CurrentUser,
) -> LocationOut:
    row = db.get(Location, location_id)
    if not row or row.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Location not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(row, k, v)
    db.add(row)
    db.commit()
    db.refresh(row)
    return LocationOut.model_validate(row)


# ---------- Business hours ----------


@router.get("/business-hours", response_model=list[BusinessHoursOut])
def list_hours(db: DbSession, user: CurrentUser) -> list[BusinessHoursOut]:
    rows = db.execute(
        select(BusinessHours)
        .where(BusinessHours.organization_id == user.organization_id)
        .order_by(BusinessHours.day_of_week.asc())
    ).scalars().all()
    return [BusinessHoursOut.model_validate(r) for r in rows]


@router.put("/business-hours", response_model=list[BusinessHoursOut])
def set_hours(
    payload: list[BusinessHoursItem],
    db: DbSession,
    user: CurrentUser,
) -> list[BusinessHoursOut]:
    existing = db.execute(
        select(BusinessHours).where(BusinessHours.organization_id == user.organization_id)
    ).scalars().all()
    for row in existing:
        db.delete(row)
    db.flush()

    new_rows: list[BusinessHours] = []
    for item in payload:
        new_rows.append(
            BusinessHours(
                organization_id=user.organization_id,
                location_id=item.location_id,
                day_of_week=item.day_of_week,
                open_time=item.open_time,
                close_time=item.close_time,
                is_closed=item.is_closed,
            )
        )
    db.add_all(new_rows)
    db.commit()
    for r in new_rows:
        db.refresh(r)
    return [BusinessHoursOut.model_validate(r) for r in new_rows]
