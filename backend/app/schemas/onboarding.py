from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class OnboardingFAQ(BaseModel):
    question: str
    answer: str
    category: str = "general"


class OnboardingBookingRoute(BaseModel):
    treatment_name: str
    normalized_treatment_key: str
    booking_url: Optional[str] = None
    route_type: str = "consult"


class OnboardingRequest(BaseModel):
    org_name: str = Field(min_length=1)
    org_slug: str = Field(min_length=2, pattern=r"^[a-z0-9-]+$")
    admin_email: EmailStr
    admin_name: str = Field(min_length=1)
    admin_password: str = Field(min_length=8)
    location_name: str = Field(min_length=1)
    location_timezone: str = "America/New_York"
    escalation_email: Optional[EmailStr] = None
    faqs: List[OnboardingFAQ] = []
    booking_routes: List[OnboardingBookingRoute] = []
