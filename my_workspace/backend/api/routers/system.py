"""System settings router — runtime-configurable key/value pairs."""

from __future__ import annotations

import importlib.metadata
import logging
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select, text

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
    "default_cooldown_seconds": {
        "label": "Cooldown ต่อ Object (วินาที)",
        "type": int,
        "min": 10,
        "max": 600,
    },
    "default_confidence_threshold": {
        "label": "Confidence Threshold ขั้นต่ำ (%)",
        "type": int,
        "min": 10,
        "max": 95,
    },
    "stream_tier": {
        "label": "คุณภาพ Live Stream (Pilot's Console)",
        "type": str,
        "options": ["THUMBNAIL", "MONITOR", "DETAIL"],
    },
    "evidence_tier": {
        "label": "คุณภาพหลักฐาน (Snapshot & Clip)",
        "type": str,
        "options": ["MONITOR", "DETAIL", "EVIDENCE"],
        # Requires server restart to take effect (CameraThread reads at startup)
    },
    "clip_crf": {
        "label": "Video CRF (18=ดีสุด/ไฟล์ใหญ่, 28=เล็กสุด/คุณภาพต่ำ)",
        "type": int,
        "min": 18,
        "max": 28,
    },
    "clip_pre_seconds": {
        "label": "Clip — บันทึกก่อน detect (วินาที)",
        "type": int,
        "min": 2,
        "max": 30,
    },
    "clip_post_seconds": {
        "label": "Clip — บันทึกหลัง detect (วินาที)",
        "type": int,
        "min": 2,
        "max": 30,
    },
}


# ── Schemas ───────────────────────────────────────────────────────────────────

class SystemSettingRead(BaseModel):
    key: str
    value: str
    label: str
    type_hint: str          # "int" | "str"
    options: list[str] | None = None   # for str enum settings
    min: int | None = None             # for int range settings
    max: int | None = None
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
        out.append(SystemSettingRead(
            key=key,
            value=row.value if row else "",
            label=meta["label"],
            type_hint=meta["type"].__name__,
            options=meta.get("options"),
            min=meta.get("min"),
            max=meta.get("max"),
            updated_by=row.updated_by if row else None,
            updated_at=row.updated_at if row else datetime.now(timezone.utc),
        ))
    return out


@router.patch("/settings", response_model=SystemSettingRead,
              dependencies=[require("system:write")])
async def update_setting(body: SystemSettingUpdate, request: Request, db: DBDep, user: CurrentUser) -> SystemSettingRead:
    """Update a single configurable system setting."""
    meta = _ALLOWED.get(body.key)
    if meta is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown setting key: {body.key!r}")

    # Type + range/enum validation
    try:
        cast = meta["type"](body.value)
    except (ValueError, TypeError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Value must be {meta['type'].__name__}")
    if "options" in meta:
        if cast not in meta["options"]:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"Value must be one of {meta['options']}")
    elif "min" in meta:
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

    # Live-reload — publish CONFIG_CHANGED so subscribers update in-memory defaults immediately
    _LIVE_RELOAD_KEYS = {"stream_tier", "evidence_tier",
                         "default_cooldown_seconds", "default_confidence_threshold"}
    if body.key in _LIVE_RELOAD_KEYS:
        from protocol.mtp import MTPMessage, MTPMsgType
        bus = request.app.state.bus
        await bus.publish(MTPMessage(
            msg_type=MTPMsgType.CONFIG_CHANGED,
            payload={"scope": "system_setting", "key": body.key, "value": str(cast)},
            source="system_router",
        ))

    return SystemSettingRead(
        key=existing.key, value=existing.value, label=meta["label"],
        type_hint=meta["type"].__name__,
        options=meta.get("options"),
        min=meta.get("min"),
        max=meta.get("max"),
        updated_by=existing.updated_by, updated_at=existing.updated_at,
    )


# ── System Info (Admin) ───────────────────────────────────────────────────────

def _pkg_version(name: str) -> str:
    """Return installed package version or '?' if not found."""
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "?"


def _dir_size_mb(path: Path) -> float:
    """Return total size of a directory in MB, 0 if not exists."""
    try:
        total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
        return round(total / 1_048_576, 2)
    except Exception:
        return 0.0


@router.get("/info", dependencies=[require("system:read")])
async def system_info(request: Request, db: DBDep) -> dict:
    """
    Return detailed system information for administrators.
    Includes database engine, library versions, storage, and environment.
    """
    cfg = request.app.state.cfg
    # Parse dialect from DATABASE_URL without touching the engine object
    # e.g. "postgresql+asyncpg://..." → "postgresql"
    #      "sqlite+aiosqlite://..."   → "sqlite"
    db_url_str: str = cfg.database_url
    dialect_name: str = db_url_str.split("+")[0].split(":")[0].lower()

    # ── Database version ──────────────────────────────────────────────────────
    db_version: str = "unknown"
    db_size_mb: float | None = None
    try:
        if dialect_name == "postgresql":
            row = await db.execute(text("SELECT version()"))
            db_version = row.scalar_one()
            row2 = await db.execute(
                text("SELECT pg_size_pretty(pg_database_size(current_database()))")
            )
            db_size_mb = row2.scalar_one()   # already human-readable from pg
        elif dialect_name == "sqlite":
            row = await db.execute(text("SELECT sqlite_version()"))
            db_version = f"SQLite {row.scalar_one()}"
            # SQLite file size
            db_url: str = cfg.database_url
            if "///" in db_url:
                db_path = Path(db_url.split("///")[-1])
                if db_path.exists():
                    db_size_mb = round(db_path.stat().st_size / 1_048_576, 2)
    except Exception as exc:
        db_version = f"query error: {exc}"

    # ── Table row counts (lightweight) ───────────────────────────────────────
    table_counts: dict[str, int] = {}
    _tables = ["cameras", "zones", "rules", "events", "users", "audit_logs"]
    for tbl in _tables:
        try:
            r = await db.execute(text(f"SELECT COUNT(*) FROM {tbl}"))
            table_counts[tbl] = r.scalar_one()
        except Exception:
            table_counts[tbl] = -1

    # ── Storage ───────────────────────────────────────────────────────────────
    snapshot_mb = _dir_size_mb(cfg.snapshot_dir)
    clip_mb     = _dir_size_mb(cfg.clip_dir)

    disk = shutil.disk_usage(str(cfg.snapshot_dir.parent) if cfg.snapshot_dir.parent.exists() else ".")
    disk_total_gb  = round(disk.total  / 1_073_741_824, 1)
    disk_used_gb   = round(disk.used   / 1_073_741_824, 1)
    disk_free_gb   = round(disk.free   / 1_073_741_824, 1)

    # ── AI model ──────────────────────────────────────────────────────────────
    model_path: Path = cfg.model_path
    ai_model_ok = model_path.exists()

    # ── Python & library versions ─────────────────────────────────────────────
    python_version = sys.version.split()[0]   # e.g. "3.12.3"

    libraries = {
        "fastapi":         _pkg_version("fastapi"),
        "sqlalchemy":      _pkg_version("sqlalchemy"),
        "asyncpg":         _pkg_version("asyncpg"),
        "aiosqlite":       _pkg_version("aiosqlite"),
        "pydantic":        _pkg_version("pydantic"),
        "uvicorn":         _pkg_version("uvicorn"),
        "alembic":         _pkg_version("alembic"),
        "openvino":        _pkg_version("openvino"),
        "opencv-python":   (
            v if (v := _pkg_version("opencv-python-headless")) != "?"
            else _pkg_version("opencv-python")
        ),
        "psutil":          _pkg_version("psutil"),
        "cryptography":    _pkg_version("cryptography"),
        "python-jose":     _pkg_version("python-jose"),
    }

    # ── Environment ───────────────────────────────────────────────────────────
    return {
        "app": {
            "name":        cfg.app_name,
            "version":     cfg.app_version,
            "environment": cfg.environment,
            "debug":       cfg.debug,
            "base_url":    cfg.base_url,
        },
        "database": {
            "engine":      dialect_name,          # "postgresql" | "sqlite"
            "url_masked":  _mask_db_url(cfg.database_url),
            "version":     db_version,
            "size":        db_size_mb,            # MB (sqlite) or "x MB" string (pg)
            "table_counts": table_counts,
        },
        "ai": {
            "model_path":     str(cfg.model_path),
            "model_loaded":   ai_model_ok,
            "model_device":   cfg.model_device,
            "confidence":     cfg.ai_confidence_threshold,
        },
        "storage": {
            "snapshot_dir":     str(cfg.snapshot_dir),
            "snapshot_size_mb": snapshot_mb,
            "clip_dir":         str(cfg.clip_dir),
            "clip_size_mb":     clip_mb,
            "disk_total_gb":    disk_total_gb,
            "disk_used_gb":     disk_used_gb,
            "disk_free_gb":     disk_free_gb,
        },
        "runtime": {
            "python_version": python_version,
            "platform":       platform.platform(),
            "architecture":   platform.machine(),
            "cpu_count":      os.cpu_count(),
            "libraries":      libraries,
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _mask_db_url(url: str) -> str:
    """Hide password in DATABASE_URL for safe display."""
    import re
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:****@", url)
