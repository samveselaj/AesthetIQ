from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.common import ORMModel


class BookingRouteBase(BaseModel):
    treatment_name: str = Field(min_length=1, max_length=255)
    normalized_treatment_key: str = Field(min_length=1, max_length=128)
    route_type: str = "consult"  # consult | direct_booking | callback
    booking_url: Optional[str] = None
    fallback_message: Optional[str] = None
    is_active: bool = True
    location_id: Optional[UUID] = None


class BookingRouteCreate(BookingRouteBase):
    pass


class BookingRouteUpdate(BaseModel):
    treatment_name: Optional[str] = None
    normalized_treatment_key: Optional[str] = None
    route_type: Optional[str] = None
    booking_url: Optional[str] = None
    fallback_message: Optional[str] = None
    is_active: Optional[bool] = None
    location_id: Optional[UUID] = None


class BookingRouteOut(ORMModel):
    id: UUID
    organization_id: UUID
    location_id: Optional[UUID]
    treatment_name: str
    normalized_treatment_key: str
    route_type: str
    booking_url: Optional[str]
    fallback_message: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
