"""Zone ORM model — detection region polygon."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class Zone(TimestampMixin, Base):
    __tablename__ = "zones"

    id: Mapped[int] = mapped_column(primary_key=True)
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # JSON array of [[x,y], ...] normalised 0.0–1.0
    coordinates: Mapped[str] = mapped_column(Text, nullable=False)
    color: Mapped[str] = mapped_column(String(16), default="#FF6B6B", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    camera: Mapped["Camera"] = relationship(back_populates="zones")
    rules: Mapped[list["Rule"]] = relationship(back_populates="zone", cascade="all, delete-orphan")
