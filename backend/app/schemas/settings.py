from __future__ import annotations

from datetime import datetime, time
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class OrgSettingsUpdate(BaseModel):
    brand_name: Optional[str] = None
    default_location_id: Optional[UUID] = None
    tone_of_voice: Optional[str] = None
    disclaimers: Optional[str] = None
    escalation_message: Optional[str] = None
    booking_cta_style: Optional[str] = None
    ai_enabled: Optional[bool] = None
    auto_send_replies: Optional[bool] = None
    collect_name: Optional[bool] = None
    collect_email: Optional[bool] = None
    collect_treatment_interest: Optional[bool] = None


class OrgSettingsOut(ORMModel):
    id: UUID
    organization_id: UUID
    brand_name: str
    default_location_id: Optional[UUID]
    tone_of_voice: str
    disclaimers: str
    escalation_message: str
    booking_cta_style: str
    ai_enabled: bool
    auto_send_replies: bool
    collect_name: bool
    collect_email: bool
    collect_treatment_interest: bool


class BusinessHoursItem(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    open_time: Optional[time] = None
    close_time: Optional[time] = None
    is_closed: bool = False
    location_id: Optional[UUID] = None


class BusinessHoursOut(BusinessHoursItem, ORMModel):
    id: UUID
    organization_id: UUID


class LocationCreate(BaseModel):
    name: str
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    timezone: str = "America/New_York"


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None


class LocationOut(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    phone_number: Optional[str]
    email: Optional[str]
    address: Optional[str]
    timezone: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EscalationRuleBase(BaseModel):
    name: str
    trigger_type: str
    conditions: Optional[dict] = None
    notify_email: Optional[EmailStr] = None
    notify_phone: Optional[str] = None
    notify_slack_webhook: Optional[str] = None
    is_active: bool = True


class EscalationRuleCreate(EscalationRuleBase):
    pass


class EscalationRuleOut(EscalationRuleBase, ORMModel):
    id: UUID
    organization_id: UUID
    created_at: datetime
    updated_at: datetime
