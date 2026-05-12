"""Health and system metrics endpoint."""

from __future__ import annotations

import platform
import time
from datetime import datetime, timezone

import psutil
from fastapi import APIRouter, Request

router = APIRouter(prefix="/health", tags=["health"])

_START = time.monotonic()


@router.get("")
async def health(request: Request) -> dict:
    state_reg = request.app.state.state_reg
    sys_state = state_reg.get_system_state()
    cam_states = state_reg.all_camera_states()

    uptime_s = int(time.monotonic() - _START)
    online = sum(1 for s in cam_states.values() if s.state == "ONLINE")

    return {
        "status": "ok",
        "version": request.app.state.cfg.app_version,
        "uptime_seconds": uptime_s,
        "boot_state": sys_state.boot_state,
        "cameras": {
            "total": len(cam_states),
            "online": online,
        },
        "system": {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_percent": psutil.virtual_memory().percent,
            "platform": platform.system(),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
