"""Strict Pydantic schemas for every AI output. The AI service MUST validate
responses against these before returning them — this is the safety boundary."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Intent = Literal[
    "pricing",
    "availability",
    "treatment_info",
    "booking",
    "existing_appointment",
    "complaint",
    "medical_concern",
    "general_question",
    "human_request",
    "unknown",
]

Urgency = Literal["low", "medium", "high"]


class ClassificationResult(BaseModel):
    intent: Intent = "unknown"
    urgency: Urgency = "low"
    needs_escalation: bool = False
    escalation_reason: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    treatment_interest: Optional[str] = None
    lead_stage_hint: Optional[str] = None


class ExtractionResult(BaseModel):
    first_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    treatment_interest: Optional[str] = None
    preferred_location: Optional[str] = None
    preferred_timeframe: Optional[str] = None
    new_or_returning: Optional[Literal["new", "returning", "unknown"]] = None


class DraftResult(BaseModel):
    reply_text: str = Field(min_length=1, max_length=2000)
    should_send_booking_link: bool = False
    booking_route_key: Optional[str] = None
    ask_followup_question: bool = False
    followup_question: Optional[str] = None
    should_escalate: bool = False
    escalation_reason: Optional[str] = None


class ClassifyRequest(BaseModel):
    message: str
    organization_id: Optional[str] = None


class DraftRequest(BaseModel):
    message: str
    organization_id: str
    conversation_id: Optional[str] = None
