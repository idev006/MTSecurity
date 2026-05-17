"""System settings router — runtime-configurable key/value pairs."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from api.deps import CurrentUser, DBDep, require
from models.system_setting import SystemSetting

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["system"])

# ── Allowed keys with validation constraints ──────────────────────────────────

_ALLOWED: dict[str, dict] = {
    "jwt_access_token_expire_minutes": {
        "label": "Access token expiry (minutes)",
        "type": int,
        "min": 5,
        "max": 1440,
    },
    "jwt_refresh_token_expire_days": {
        "label": "Refresh token expiry (days)",
        "type": int,
        "min": 1,
        "max": 90,
    },
}


# ── Schemas ───────────────────────────────────────────────────────────────────

class SystemSettingRead(BaseModel):
    key: str
    value: str
    label: str
    updated_by: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class SystemSettingUpdate(BaseModel):
    key: str
    value: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/settings", response_model=list[SystemSettingRead],
            dependencies=[require("system:read")])
async def list_settings(db: DBDep) -> list[SystemSettingRead]:
    """Return all configurable system settings with their current values."""
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.key))
    rows = {r.key: r for r in result.scalars().all()}

    out: list[SystemSettingRead] = []
    for key, meta in _ALLOWED.items():
        row = rows.get(key)
        # If not yet set in DB, return the allowed-key default
        out.append(SystemSettingRead(
            key=key,
            value=row.value if row else "",
            label=meta["label"],
            updated_by=row.updated_by if row else None,
            updated_at=row.updated_at if row else datetime.now(timezone.utc),
        ))
    return out


@router.patch("/settings", response_model=SystemSettingRead,
              dependencies=[require("system:write")])
async def update_setting(body: SystemSettingUpdate, db: DBDep, user: CurrentUser) -> SystemSettingRead:
    """Update a single configurable system setting."""
    meta = _ALLOWED.get(body.key)
    if meta is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown setting key: {body.key!r}")

    # Type + range validation
    try:
        cast = meta["type"](body.value)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Value must be {meta['type'].__name__}")
    if cast < meta["min"] or cast > meta["max"]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Value must be between {meta['min']} and {meta['max']}")

    now = datetime.now(timezone.utc)
    existing = await db.get(SystemSetting, body.key)
    if existing is None:
        existing = SystemSetting(key=body.key, value=str(cast),
                                 updated_by=user.username, updated_at=now)
        db.add(existing)
    else:
        existing.value = str(cast)
        existing.updated_by = user.username
        existing.updated_at = now

    await db.commit()
    await db.refresh(existing)

    logger.info("System setting updated: %s=%s by %s", body.key, cast, user.username)
    return SystemSettingRead(
        key=existing.key, value=existing.value, label=meta["label"],
        updated_by=existing.updated_by, updated_at=existing.updated_at,
    )
