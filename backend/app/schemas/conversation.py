from __future__ import annotations

from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel
from app.schemas.lead import LeadOut


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    channel_type: str = "sms"


class MessageOut(ORMModel):
    id: UUID
    conversation_id: UUID
    lead_id: UUID
    direction: str
    sender_type: str
    channel_type: str
    content: str
    delivery_status: str
    ai_generated: bool
    reviewed_by_human: bool
    created_at: datetime


class ConversationOut(ORMModel):
    id: UUID
    organization_id: UUID
    lead_id: UUID
    channel_type: str
    status: str
    ai_enabled: bool
    escalation_state: str
    ai_mode: str  # "active" | "paused" | "escalated" — derived from ai_enabled + escalation_state
    created_at: datetime
    updated_at: datetime


class ConversationDetail(ConversationOut):
    lead: LeadOut
    messages: List[MessageOut]


class ConversationListItem(ConversationOut):
    lead_name: Optional[str] = None
    lead_phone: Optional[str] = None
    last_message_preview: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_from_lead: bool = False


class AIDraftPreview(BaseModel):
    reply_text: str
    should_send_booking_link: bool = False
    booking_url: Optional[str] = None
    should_escalate: bool = False
    escalation_reason: Optional[str] = None
    ask_followup_question: bool = False
    followup_question: Optional[str] = None
    classification: Optional[dict[str, Any]] = None
