from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    new_leads_today: int
    contacted_today: int
    booked_today: int
    escalated_today: int
    avg_first_response_seconds: Optional[float] = None
    inbox_open: int
    # Owner-friendly weekly metrics
    conversations_handled_7d: int
    missed_calls_recovered_7d: int
    booking_links_sent_7d: int
    booked_7d: int
    ai_handled_pct_7d: Optional[float] = None


class InboxSummaryItem(BaseModel):
    conversation_id: UUID
    lead_id: UUID
    lead_name: Optional[str]
    preview: Optional[str]
    escalated: bool
    waiting_on_staff: bool
