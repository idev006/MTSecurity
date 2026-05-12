"""StateRegistry — in-memory runtime state (no persistence)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import auto
from typing import Any


class CameraState:
    INACTIVE = "INACTIVE"
    CONNECTING = "CONNECTING"
    ONLINE = "ONLINE"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"
    FAILED = "FAILED"

    VALID_TRANSITIONS: dict[str, list[str]] = {
        INACTIVE:     [CONNECTING],
        CONNECTING:   [ONLINE, ERROR, FAILED],
        ONLINE:       [RECONNECTING, INACTIVE],
        RECONNECTING: [ONLINE, ERROR, FAILED],
        ERROR:        [RECONNECTING, FAILED, INACTIVE],
        FAILED:       [INACTIVE],
    }

    @classmethod
    def is_valid_transition(cls, current: str, next_: str) -> bool:
        return next_ in cls.VALID_TRANSITIONS.get(current, [])


@dataclass
class CameraRuntimeState:
    state: str = CameraState.INACTIVE
    fps: float = 0.0
    latency_ms: float = 0.0
    reconnect_attempts: int = 0
    last_frame_at: datetime | None = None
    error_msg: str | None = None


@dataclass
class SystemRuntimeState:
    boot_state: str = "INITIALIZING"
    active_cameras: int = 0
    ai_queue_size: int = 0
    uptime_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class StateRegistry:
    """
    Thread-safe in-memory registry for all runtime state.
    Resets on restart — persistent config lives in ConfigService.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cameras: dict[int, CameraRuntimeState] = {}
        self._system = SystemRuntimeState()
        self._custom: dict[str, Any] = {}

    # ── Camera ────────────────────────────────────────────────────────────────

    def get_camera_state(self, camera_id: int) -> CameraRuntimeState:
        with self._lock:
            if camera_id not in self._cameras:
                self._cameras[camera_id] = CameraRuntimeState()
            return self._cameras[camera_id]

    def transition_camera(self, camera_id: int, new_state: str, **kwargs: Any) -> bool:
        with self._lock:
            cam = self._cameras.setdefault(camera_id, CameraRuntimeState())
            if not CameraState.is_valid_transition(cam.state, new_state):
                return False
            cam.state = new_state
            for k, v in kwargs.items():
                if hasattr(cam, k):
                    setattr(cam, k, v)
            return True

    def all_camera_states(self) -> dict[int, CameraRuntimeState]:
        with self._lock:
            return dict(self._cameras)

    # ── System ────────────────────────────────────────────────────────────────

    def set_boot_state(self, state: str) -> None:
        with self._lock:
            self._system.boot_state = state

    def get_system_state(self) -> SystemRuntimeState:
        with self._lock:
            return self._system

    def update_system(self, **kwargs: Any) -> None:
        with self._lock:
            for k, v in kwargs.items():
                if hasattr(self._system, k):
                    setattr(self._system, k, v)

    # ── Custom key-value ─────────────────────────────────────────────────────

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._custom[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._custom.get(key, default)
