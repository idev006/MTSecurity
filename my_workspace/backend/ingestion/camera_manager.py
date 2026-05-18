"""CameraManager — lifecycle controller for all CameraThreads."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from cryptography.fernet import Fernet

from ingestion.camera_thread import CameraThread
from ingestion.clip_buffer import ClipBuffer
from ingestion.frame_buffer import FrameBuffer
from protocol.mtp import MTPMessage, MTPMsgType
from ssot.state_registry import StateRegistry

if TYPE_CHECKING:
    from protocol.message_bus import MessageBus
    from ssot.config_service import ConfigService

logger = logging.getLogger(__name__)


class CameraManager:
    """
    Manages all CameraThread instances.

    - start_all(): reads active cameras from ConfigService, starts a thread each
    - stop_all(): signals all threads to stop gracefully
    - Subscribes to CONFIG_CHANGED so camera add/remove/update takes effect live

    Supports both RTSP and local webcam sources transparently.
    """

    def __init__(
        self,
        buffer: FrameBuffer,
        config_svc: "ConfigService",
        state_reg: StateRegistry,
        bus: "MessageBus",
        encryption_key: bytes,
        clip_buffer: ClipBuffer | None = None,
        hires_buffer: FrameBuffer | None = None,
        evidence_tier: str = "DETAIL",
        stream_buffer: FrameBuffer | None = None,
        stream_tier: str = "MONITOR",
    ) -> None:
        self._buffer = buffer
        self._clip_buffer = clip_buffer
        self._hires_buffer = hires_buffer
        self._evidence_tier = evidence_tier
        self._stream_buffer = stream_buffer
        self._stream_tier = stream_tier
        self._config = config_svc
        self._state = state_reg
        self._bus = bus
        self._fernet = Fernet(encryption_key)
        self._threads: dict[int, CameraThread] = {}

    async def start_all(self) -> None:
        cameras = await self._config.get_active_cameras()
        for cam in cameras:
            await self._start_camera(cam)

        self._bus.subscribe(MTPMsgType.CONFIG_CHANGED, self._on_config_changed)
        logger.info("CameraManager: started %d camera threads", len(self._threads))

    async def stop_all(self) -> None:
        for thread in self._threads.values():
            thread.stop()
        for cid, thread in self._threads.items():
            thread.join(timeout=5)
            logger.info("Camera %d thread stopped", cid)
        self._threads.clear()

    async def start_camera(self, camera_id: int) -> None:
        cam = await self._config.get_camera(camera_id)
        if cam and cam.is_active:
            await self._start_camera(cam)

    def stop_camera(self, camera_id: int) -> None:
        thread = self._threads.pop(camera_id, None)
        if thread:
            thread.stop()
            self._buffer.remove(camera_id)
            if self._clip_buffer is not None:
                self._clip_buffer.remove(camera_id)
            if self._hires_buffer is not None:
                self._hires_buffer.remove(camera_id)
            if self._stream_buffer is not None:
                self._stream_buffer.remove(camera_id)
            logger.info("Camera %d stopped", camera_id)

    async def restart_camera(self, camera_id: int) -> None:
        """Stop (if running) then restart a camera. Used by WebcamWatcher."""
        self.stop_camera(camera_id)
        await self.start_camera(camera_id)

    async def remap_camera_index(self, camera_id: int, new_index: int) -> None:
        """Update device_index in DB then restart the camera thread.

        Called by WebcamWatcher when a device reappears at a different index.
        """
        cam = await self._config.get_camera(camera_id)
        if cam is None:
            logger.warning("remap_camera_index: camera %d not found", camera_id)
            return
        # Persist the new index via ConfigService so CameraThread uses the right device
        await self._config.update_camera(
            camera_id,
            {"device_index": new_index},
            actor="webcam-watcher",
        )
        self.stop_camera(camera_id)
        await self.start_camera(camera_id)
        logger.info("Camera %d remapped to device index %d", camera_id, new_index)

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _start_camera(self, cam) -> None:
        """Start a CameraThread for the given Camera ORM object."""
        camera_id = cam.id
        if camera_id in self._threads and self._threads[camera_id].is_alive():
            return   # already running

        source_type = getattr(cam, "source_type", "rtsp")
        rtsp_url: str | None = None

        if source_type == "webcam":
            device_index = cam.device_index
            if device_index is None:
                logger.error("Camera %d (webcam): device_index not set", camera_id)
                return
            thread = CameraThread(
                camera_id=camera_id,
                buffer=self._buffer,
                state_reg=self._state,
                bus=self._bus,
                source_type="webcam",
                device_index=device_index,
                target_fps=cam.fps,
                clip_buffer=self._clip_buffer,
                hires_buffer=self._hires_buffer,
                evidence_tier=self._evidence_tier,
                stream_buffer=self._stream_buffer,
                stream_tier=self._stream_tier,
            )
        else:
            # RTSP — decrypt URL before passing to thread
            if not cam.rtsp_url_encrypted:
                logger.error("Camera %d (rtsp): rtsp_url_encrypted is null", camera_id)
                return
            try:
                rtsp_url = self._fernet.decrypt(cam.rtsp_url_encrypted.encode()).decode()
            except Exception:
                logger.error("Camera %d: failed to decrypt RTSP URL", camera_id)
                return
            thread = CameraThread(
                camera_id=camera_id,
                buffer=self._buffer,
                state_reg=self._state,
                bus=self._bus,
                source_type="rtsp",
                rtsp_url=rtsp_url,
                target_fps=cam.fps,
                clip_buffer=self._clip_buffer,
                hires_buffer=self._hires_buffer,
                evidence_tier=self._evidence_tier,
                stream_buffer=self._stream_buffer,
                stream_tier=self._stream_tier,
            )

        self._threads[camera_id] = thread
        thread.start()

    async def _restart_all_cameras(self) -> None:
        """Stop and restart every active camera thread to apply new encoding settings."""
        camera_ids = list(self._threads.keys())
        for camera_id in camera_ids:
            self.stop_camera(camera_id)
            await self.start_camera(camera_id)
        logger.info("All %d camera thread(s) restarted with updated encoding settings", len(camera_ids))

    async def _on_config_changed(self, msg: MTPMessage) -> None:
        payload = msg.payload
        scope = payload.get("scope")

        # Live-reload tier settings (stream_tier / evidence_tier)
        if scope == "system_setting":
            key = payload.get("key")
            value = payload.get("value", "")
            if key == "stream_tier":
                self._stream_tier = value
                logger.info("stream_tier → %s — restarting camera threads", value)
                await self._restart_all_cameras()
            elif key == "evidence_tier":
                self._evidence_tier = value
                logger.info("evidence_tier → %s — restarting camera threads", value)
                await self._restart_all_cameras()
            return

        if scope != "camera":
            return

        camera_id = payload.get("entity_id")
        if camera_id is None:
            return

        changes = payload.get("changes", {})

        if changes.get("is_active") is False:
            self.stop_camera(camera_id)
            return

        if "is_active" in changes or "rtsp_url_encrypted" in changes or "device_index" in changes:
            self.stop_camera(camera_id)
            await self.start_camera(camera_id)

    @property
    def active_count(self) -> int:
        return sum(1 for t in self._threads.values() if t.is_alive())
