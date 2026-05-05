from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class FAQBase(BaseModel):
    category: str = "general"
    question: str = Field(min_length=1, max_length=500)
    answer: str = Field(min_length=1)
    tags: Optional[List[str]] = None
    is_active: bool = True
    priority: int = 100
    location_id: Optional[UUID] = None


class FAQCreate(FAQBase):
    pass


class FAQUpdate(BaseModel):
    category: Optional[str] = None
    question: Optional[str] = None
    answer: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None
    location_id: Optional[UUID] = None


class FAQOut(ORMModel):
    id: UUID
    organization_id: UUID
    location_id: Optional[UUID]
    category: str
    question: str
    answer: str
    tags: Optional[List[str]]
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime
