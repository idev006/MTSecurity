"""User Pydantic v2 schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(..., min_length=8)
    role: str = Field("OPERATOR", pattern=r"^(SUPERADMIN|ADMIN|OPERATOR|AUDITOR|EXTERNAL_SYSTEM)$")
    display_name: str | None = None
    camera_scope: str | None = None   # comma-separated camera IDs


class UserUpdate(BaseModel):
    display_name: str | None = None
    is_active: bool | None = None
    camera_scope: str | None = None


class UserRead(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    display_name: str | None
    camera_scope: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int   # seconds


class LoginRequest(BaseModel):
    username: str
    password: str
