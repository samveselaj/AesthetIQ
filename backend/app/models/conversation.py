from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel_type: Mapped[str] = mapped_column(String(32), nullable=False, default="sms")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    ai_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    escalation_state: Mapped[str] = mapped_column(String(32), nullable=False, default="none")

    @property
    def ai_mode(self) -> str:
        # Derived view of AI state for the UI: "escalated" wins over "paused".
        if self.escalation_state == "escalated":
            return "escalated"
        return "active" if self.ai_enabled else "paused"


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    direction: Mapped[str] = mapped_column(String(16), nullable=False)
    sender_type: Mapped[str] = mapped_column(String(16), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(32), nullable=False, default="sms")

    content: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    delivery_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewed_by_human: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
