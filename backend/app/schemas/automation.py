from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class MessageTemplateBase(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    template_type: str
    content: str
    variables: Optional[dict[str, Any]] = None
    is_active: bool = True


class MessageTemplateCreate(MessageTemplateBase):
    pass


class MessageTemplateUpdate(BaseModel):
    name: Optional[str] = None
    template_type: Optional[str] = None
    content: Optional[str] = None
    variables: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class MessageTemplateOut(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    template_type: str
    content: str
    variables: Optional[dict[str, Any]]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AutomationRuleBase(BaseModel):
    name: str
    trigger_event: str
    channel_type: str = "sms"
    is_active: bool = True
    delay_minutes: int = 0
    template_id: Optional[UUID] = None
    conditions: Optional[dict[str, Any]] = None


class AutomationRuleCreate(AutomationRuleBase):
    pass


class AutomationRuleUpdate(BaseModel):
    name: Optional[str] = None
    trigger_event: Optional[str] = None
    channel_type: Optional[str] = None
    is_active: Optional[bool] = None
    delay_minutes: Optional[int] = None
    template_id: Optional[UUID] = None
    conditions: Optional[dict[str, Any]] = None


class AutomationRuleOut(ORMModel):
    id: UUID
    organization_id: UUID
    name: str
    trigger_event: str
    channel_type: str
    is_active: bool
    delay_minutes: int
    template_id: Optional[UUID]
    conditions: Optional[dict[str, Any]]
    created_at: datetime
    updated_at: datetime
