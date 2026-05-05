from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk


class Lead(Base, TimestampMixin):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # source
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # identity
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)

    preferred_contact_method: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    treatment_interest: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # lifecycle
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="new")
    lifecycle_stage: Mapped[str] = mapped_column(String(32), nullable=False, default="inquiry")
    booking_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_sent")
    do_not_contact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    assigned_to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    last_inbound_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_outbound_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class LeadTag(Base, TimestampMixin):
    __tablename__ = "lead_tags"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_tag_org_name"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[str] = mapped_column(String(16), nullable=False, default="#3b82f6")


class LeadTagAssignment(Base):
    __tablename__ = "lead_tag_assignments"
    __table_args__ = (UniqueConstraint("lead_id", "tag_id", name="uq_lead_tag"),)

    lead_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("lead_tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
