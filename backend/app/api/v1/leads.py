from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.core.deps import CurrentUser, DbSession
from app.models.lead import Lead
from app.schemas.common import Page
from app.schemas.lead import LeadCreate, LeadOut, LeadUpdate
from app.services.lead_service import find_or_create_lead

router = APIRouter(prefix="/leads", tags=["leads"])


@router.get("", response_model=Page[LeadOut])
def list_leads(
    db: DbSession,
    user: CurrentUser,
    status_filter: Optional[str] = Query(None, alias="status"),
    source: Optional[str] = None,
    treatment: Optional[str] = None,
    search: Optional[str] = None,
    assigned_to: Optional[UUID] = None,
    limit: int = Query(50, le=200, ge=1),
    offset: int = Query(0, ge=0),
) -> Page[LeadOut]:
    stmt = select(Lead).where(Lead.organization_id == user.organization_id)
    count_stmt = select(func.count(Lead.id)).where(Lead.organization_id == user.organization_id)
    if status_filter:
        stmt = stmt.where(Lead.status == status_filter)
        count_stmt = count_stmt.where(Lead.status == status_filter)
    if source:
        stmt = stmt.where(Lead.source_type == source)
        count_stmt = count_stmt.where(Lead.source_type == source)
    if treatment:
        stmt = stmt.where(Lead.treatment_interest == treatment)
        count_stmt = count_stmt.where(Lead.treatment_interest == treatment)
    if assigned_to:
        stmt = stmt.where(Lead.assigned_to_user_id == assigned_to)
        count_stmt = count_stmt.where(Lead.assigned_to_user_id == assigned_to)
    if search:
        like = f"%{search.lower()}%"
        pred = or_(
            func.lower(Lead.full_name).like(like),
            func.lower(Lead.first_name).like(like),
            func.lower(Lead.email).like(like),
            Lead.phone.like(f"%{search}%"),
        )
        stmt = stmt.where(pred)
        count_stmt = count_stmt.where(pred)

    total = db.execute(count_stmt).scalar_one()
    rows = db.execute(stmt.order_by(Lead.created_at.desc()).limit(limit).offset(offset)).scalars().all()
    return Page[LeadOut](items=[LeadOut.model_validate(r) for r in rows], total=total, limit=limit, offset=offset)


@router.post("", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, db: DbSession, user: CurrentUser) -> LeadOut:
    result = find_or_create_lead(
        db,
        organization_id=user.organization_id,
        source_type=payload.source_type,
        source_label=payload.source_label,
        phone=payload.phone,
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        full_name=payload.full_name,
        location_id=payload.location_id,
        treatment_interest=payload.treatment_interest,
    )
    db.commit()
    db.refresh(result.lead)
    return LeadOut.model_validate(result.lead)


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: UUID, db: DbSession, user: CurrentUser) -> LeadOut:
    lead = db.get(Lead, lead_id)
    if not lead or lead.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found")
    return LeadOut.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    db: DbSession,
    user: CurrentUser,
) -> LeadOut:
    lead = db.get(Lead, lead_id)
    if not lead or lead.organization_id != user.organization_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead not found")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(lead, k, v)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return LeadOut.model_validate(lead)
