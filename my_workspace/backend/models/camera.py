"""Camera ORM model."""

from __future__ import annotations

from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class Camera(TimestampMixin, Base):
    __tablename__ = "cameras"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    # "rtsp" | "webcam"
    source_type: Mapped[str] = mapped_column(String(16), nullable=False, default="rtsp")
    # Encrypted RTSP URL — null for webcam sources
    rtsp_url_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Local webcam device index (0-9) — null for RTSP sources
    device_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Stable device fingerprint from WMI/DirectShow — survives index changes
    device_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    resolution_width: Mapped[int] = mapped_column(Integer, default=1920, nullable=False)
    resolution_height: Mapped[int] = mapped_column(Integer, default=1080, nullable=False)
    fps: Mapped[float] = mapped_column(Float, default=15.0, nullable=False)

    # Runtime state tracked in StateRegistry (not persisted)
    zones: Mapped[list["Zone"]] = relationship(back_populates="camera", cascade="all, delete-orphan")
    events: Mapped[list["Event"]] = relationship(back_populates="camera")
