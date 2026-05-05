from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk


class EscalationRule(Base, TimestampMixin):
    __tablename__ = "escalation_rules"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    # medical | pricing_exception | complaint | human_request | off_script
    # | existing_client_issue | urgent
    trigger_type: Mapped[str] = mapped_column(String(64), nullable=False)
    conditions: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    notify_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notify_phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    notify_slack_webhook: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
