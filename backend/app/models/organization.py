from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Time, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk


class Organization(Base, TimestampMixin):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    subscription_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="trialing"
    )
    lemon_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, unique=True
    )
    trial_ends_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    settings: Mapped[Optional["OrgSettings"]] = relationship(
        back_populates="organization", uselist=False, cascade="all, delete-orphan"
    )


class OrgSettings(Base, TimestampMixin):
    __tablename__ = "org_settings"

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    brand_name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), nullable=True
    )

    tone_of_voice: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=(
            "Warm, concise, professional, premium-but-approachable. Never robotic, "
            "never aggressive, never clinical advice."
        ),
    )
    disclaimers: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=(
            "Messages are assistive and non-diagnostic. For medical concerns or "
            "possible side effects, we will connect you with our team."
        ),
    )
    escalation_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=(
            "Thanks for your message. I'm flagging this for our team now so they "
            "can help you directly as soon as possible."
        ),
    )
    booking_cta_style: Mapped[str] = mapped_column(String(32), nullable=False, default="soft")

    ai_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_send_replies: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    collect_name: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    collect_email: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    collect_treatment_interest: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )

    organization: Mapped[Organization] = relationship(back_populates="settings")


class BusinessHours(Base, TimestampMixin):
    __tablename__ = "business_hours"
    __table_args__ = (
        UniqueConstraint("organization_id", "location_id", "day_of_week", name="uq_hours_day"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    organization_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    location_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("locations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0 = Mon … 6 = Sun
    open_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    close_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
