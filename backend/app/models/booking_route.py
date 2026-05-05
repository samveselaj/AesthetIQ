from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, uuid_pk


class BookingRoute(Base, TimestampMixin):
    __tablename__ = "booking_routes"

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
    )

    treatment_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_treatment_key: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )

    # consult | direct_booking | callback
    route_type: Mapped[str] = mapped_column(String(32), nullable=False, default="consult")
    booking_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    fallback_message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=(
            "Our team will reach out to help you book. Can you share a good time "
            "to call you back?"
        ),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
