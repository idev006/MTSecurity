"""Rule ORM model — links a behavior to a zone with thresholds."""

from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class Rule(TimestampMixin, Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    behavior: Mapped[str] = mapped_column(String(64), nullable=False)  # "intrusion", "loitering", etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Thresholds
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.6, nullable=False)
    dwell_threshold_seconds: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    # Schedule — JSON: {"start": "22:00", "end": "06:00", "days": [0,1,2,3,4,5,6]}
    schedule: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Alert severity
    severity: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)

    zone: Mapped["Zone"] = relationship(back_populates="rules")
    events: Mapped[list["Event"]] = relationship(back_populates="rule")
