"""WebcamWatcher — background thread that polls for webcam hotplug events.

Responsibilities
----------------
- Every ``interval`` seconds, enumerate available webcam devices.
- For each registered webcam camera in FAILED / ERROR state:
    1. Try to match by ``device_name`` fingerprint (accurate, survives index change).
    2. Fall back to the stored ``device_index`` if ``device_name`` is not set.
    3. If the device is now available (possibly at a different index) → remap and restart.
- Log a warning when a registered camera's device disappears.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import TYPE_CHECKING

from ingestion.webcam_enumerator import EnumeratedDevice, enumerate_webcams, find_index_by_name
from ssot.state_registry import CameraState, StateRegistry

if TYPE_CHECKING:
    from ingestion.camera_manager import CameraManager
    from ssot.config_service import ConfigService

logger = logging.getLogger(__name__)

_RECOVERABLE = {CameraState.FAILED, CameraState.ERROR, CameraState.INACTIVE}


class WebcamWatcher(threading.Thread):
    """Polls for hotplug events and auto-restarts cameras whose device reappears."""

    def __init__(
        self,
        cam_manager: "CameraManager",
        config_svc: "ConfigService",
        state_reg: StateRegistry,
        loop: asyncio.AbstractEventLoop,
        interval: int = 15,
    ) -> None:
        super().__init__(name="webcam-watcher", daemon=True)
        self._manager = cam_manager
        self._config = config_svc
        self._state = state_reg
        self._loop = loop
        self._interval = interval
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        logger.info("WebcamWatcher started (interval=%ds)", self._interval)
        # Stagger first run so startup noise settles
        self._stop.wait(timeout=self._interval)
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception:
                logger.exception("WebcamWatcher tick error")
            self._stop.wait(timeout=self._interval)
        logger.info("WebcamWatcher stopped")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        """One poll cycle — enumerate devices, match cameras, restart if needed."""
        available = enumerate_webcams()
        available_by_name: dict[str, EnumeratedDevice] = {d.device_name: d for d in available}
        available_indices: set[int] = {d.index for d in available}

        # Fetch active webcam cameras from ConfigService (run coroutine from thread)
        cameras = self._run(self._config.get_active_cameras())
        webcams = [c for c in cameras if getattr(c, "source_type", None) == "webcam"]

        for cam in webcams:
            cam_state = self._state.get_camera_state(cam.id).state

            # ── Check for disappearing devices (informational only) ───────────
            if cam.device_index is not None and cam.device_index not in available_indices:
                if cam_state not in _RECOVERABLE:
                    logger.warning(
                        "Camera %d (%s): device index %d no longer available",
                        cam.id, cam.name, cam.device_index,
                    )

            # ── Try to recover cameras in a failed/error/inactive state ───────
            if cam_state not in _RECOVERABLE:
                continue  # already running — nothing to do

            recovered = self._find_device(cam, available_by_name, available_indices)
            if recovered is None:
                logger.debug(
                    "Camera %d (%s): device not found in current scan (state=%s)",
                    cam.id, cam.name, cam_state,
                )
                continue

            new_index = recovered.index
            if new_index != cam.device_index:
                logger.info(
                    "Camera %d (%s): index changed %s → %d — remapping",
                    cam.id, cam.name, cam.device_index, new_index,
                )
                self._run(self._manager.remap_camera_index(cam.id, new_index))
            else:
                logger.info(
                    "Camera %d (%s): device re-appeared at index %d — restarting",
                    cam.id, cam.name, new_index,
                )
                self._run(self._manager.restart_camera(cam.id))

    def _find_device(
        self,
        cam,
        available_by_name: dict[str, EnumeratedDevice],
        available_indices: set[int],
    ) -> EnumeratedDevice | None:
        """Match a camera to an available device.

        Priority:
        1. device_name fingerprint match (survives index change)
        2. device_index direct match (legacy cameras without device_name)
        """
        # 1. Fingerprint match
        name = getattr(cam, "device_name", None)
        if name and name in available_by_name:
            return available_by_name[name]

        # 2. Index fallback
        if cam.device_index is not None and cam.device_index in available_indices:
            # Return any EnumeratedDevice at that index
            for dev in available_by_name.values():
                if dev.index == cam.device_index:
                    return dev
            # available but not in by_name (shouldn't happen)
            return EnumeratedDevice(
                index=cam.device_index,
                label=f"Webcam {cam.device_index}",
                device_name=f"Webcam {cam.device_index}",
            )

        return None

    def _run(self, coro):
        """Run a coroutine from this thread on the event loop (blocking)."""
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=10)
