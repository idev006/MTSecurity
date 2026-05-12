"""User model — supports 6 actor roles."""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(
        String(32), nullable=False, default="OPERATOR"
    )  # SUPERADMIN | ADMIN | OPERATOR | AUDITOR | EXTERNAL_SYSTEM
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # scope — comma-separated camera IDs; None means all cameras
    camera_scope: Mapped[str | None] = mapped_column(String(512), nullable=True)

    api_keys: Mapped[list["APIKey"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")

    def camera_ids(self) -> list[int] | None:
        """Returns list of allowed camera IDs, or None for unrestricted."""
        if self.camera_scope is None:
            return None
        return [int(x) for x in self.camera_scope.split(",") if x.strip()]
