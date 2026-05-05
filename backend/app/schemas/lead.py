from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class LeadBase(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    preferred_contact_method: Optional[str] = None
    treatment_interest: Optional[str] = None
    notes: Optional[str] = None
    location_id: Optional[UUID] = None


class LeadCreate(LeadBase):
    source_type: str = Field(default="manual")
    source_label: Optional[str] = None


class LeadUpdate(LeadBase):
    status: Optional[str] = None
    lifecycle_stage: Optional[str] = None
    booking_status: Optional[str] = None
    do_not_contact: Optional[bool] = None
    assigned_to_user_id: Optional[UUID] = None


class LeadOut(ORMModel):
    id: UUID
    organization_id: UUID
    location_id: Optional[UUID]
    source_type: str
    source_label: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    full_name: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    preferred_contact_method: Optional[str]
    treatment_interest: Optional[str]
    status: str
    lifecycle_stage: str
    booking_status: str
    do_not_contact: bool
    assigned_to_user_id: Optional[UUID]
    notes: Optional[str]
    last_inbound_at: Optional[datetime]
    last_outbound_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
