"""CameraThread — one thread per camera source (RTSP or local webcam)."""

from __future__ import annotations

import logging
import sys
import threading
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import cv2

from ingestion.clip_buffer import ClipBuffer
from ingestion.frame_buffer import Frame, FrameBuffer
from ingestion.frame_codec import ResolutionTier, encode_frame
from protocol.mtp import MTPMessage, MTPMsgType, MTPPriority
from protocol.payloads import CameraReconnectPayload, CameraStatusPayload
from ssot.state_registry import CameraState, StateRegistry

if TYPE_CHECKING:
    from protocol.message_bus import MessageBus

logger = logging.getLogger(__name__)

# Exponential backoff for RTSP (seconds): [5,10,20,40,60,60,…]
_RTSP_BACKOFF = [5, 10, 20, 40, 60, 60, 60]
# Shorter backoff for webcams (device physically present, check frequently)
_WEBCAM_BACKOFF = [2, 2, 5, 5, 10, 10, 10]
_MAX_RETRIES = 10

# DSHOW is faster on Windows — CAP_ANY tries multiple backends sequentially
_WEBCAM_BACKEND = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY


class CameraThread(threading.Thread):
    """
    Reads a camera source in a tight loop.

    Supports two source types:
      - "rtsp":   cv2.VideoCapture(rtsp_url) with exponential backoff reconnect
      - "webcam": cv2.VideoCapture(device_index) with fast reconnect

    On each decoded frame:
      1. Encode JPEG at THUMBNAIL resolution
      2. Write to FrameBuffer (drops old frame automatically)
      3. Publish FRAME_READY on bus (NORMAL priority, 1s TTL)
    """

    def __init__(
        self,
        camera_id: int,
        buffer: FrameBuffer,
        state_reg: StateRegistry,
        bus: "MessageBus",
        source_type: str = "rtsp",
        rtsp_url: str | None = None,
        device_index: int | None = None,
        target_fps: float = 15.0,
        clip_buffer: ClipBuffer | None = None,
        hires_buffer: FrameBuffer | None = None,
        evidence_tier: str = "DETAIL",
        stream_buffer: FrameBuffer | None = None,
        stream_tier: str = "MONITOR",
    ) -> None:
        super().__init__(name=f"cam-{camera_id}", daemon=True)
        self.camera_id = camera_id
        self._buffer = buffer
        self._clip_buffer = clip_buffer
        self._hires_buffer = hires_buffer
        self._stream_buffer = stream_buffer
        self._state = state_reg
        self._bus = bus
        self._source_type = source_type
        self._rtsp_url = rtsp_url
        self._device_index = device_index
        self._frame_interval = 1.0 / max(target_fps, 1.0)
        self._stop_event = threading.Event()
        self._evidence_tier = ResolutionTier(evidence_tier)
        self._stream_tier = ResolutionTier(stream_tier)
        # Rolling FPS — exponential moving average over actual frame intervals
        self._fps_ema: float = 0.0
        self._fps_last_time: float = 0.0

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        self._state.transition_camera(self.camera_id, CameraState.CONNECTING)
        self._publish_status("connecting")
        self._connect_loop()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _open_capture(self) -> cv2.VideoCapture:
        if self._source_type == "webcam" and self._device_index is not None:
            return cv2.VideoCapture(self._device_index, _WEBCAM_BACKEND)
        return cv2.VideoCapture(self._rtsp_url)

    def _source_label(self) -> str:
        if self._source_type == "webcam":
            return f"webcam:{self._device_index}"
        return self._rtsp_url or "unknown"

    def _backoff_schedule(self) -> list[int]:
        return _WEBCAM_BACKOFF if self._source_type == "webcam" else _RTSP_BACKOFF

    def _connect_loop(self) -> None:
        attempt = 0
        backoff = self._backoff_schedule()
        while not self._stop_event.is_set() and attempt <= _MAX_RETRIES:
            cap = self._open_capture()
            if not cap.isOpened():
                self._handle_failure(attempt, cap, backoff)
                attempt += 1
                continue

            logger.info("Camera %d connected: %s", self.camera_id, self._source_label())
            self._state.transition_camera(self.camera_id, CameraState.ONLINE)
            self._publish_status("online")
            attempt = 0   # reset on success

            disconnected = self._read_loop(cap)
            cap.release()

            if disconnected and not self._stop_event.is_set():
                self._state.transition_camera(self.camera_id, CameraState.RECONNECTING)
                self._publish_status("reconnecting")

        if not self._stop_event.is_set():
            self._state.transition_camera(
                self.camera_id, CameraState.FAILED,
                error_msg=f"Max retries ({_MAX_RETRIES}) exceeded",
            )
            self._publish_status("error", error_msg=f"Failed after {_MAX_RETRIES} retries")
            logger.error("Camera %d FAILED — max retries exceeded", self.camera_id)

        self._state.transition_camera(self.camera_id, CameraState.INACTIVE)

    def _read_loop(self, cap: cv2.VideoCapture) -> bool:
        """Returns True if disconnected (should reconnect), False if stopped."""
        consecutive_fails = 0
        last_frame_time = time.monotonic()

        while not self._stop_event.is_set():
            ret, frame = cap.read()
            if not ret:
                consecutive_fails += 1
                if consecutive_fails >= 30:
                    logger.warning("Camera %d: 30 consecutive read failures", self.camera_id)
                    return True
                time.sleep(0.05)
                continue

            consecutive_fails = 0
            now = time.monotonic()
            elapsed = now - last_frame_time
            if elapsed < self._frame_interval:
                time.sleep(self._frame_interval - elapsed)
            last_frame_time = time.monotonic()

            self._process_frame(frame)

        return False

    def _process_frame(self, frame) -> None:
        try:
            h, w = frame.shape[:2]

            # THUMBNAIL → live streaming buffer (small, fast, used by AI pipeline + WebSocket)
            jpeg_thumb = encode_frame(frame, ResolutionTier.THUMBNAIL)
            f_thumb = Frame(camera_id=self.camera_id, data=jpeg_thumb, width=w, height=h)
            self._buffer.put(f_thumb)

            # Evidence tier → high-res buffer (snapshot) + clip buffer (video)
            need_hires = self._hires_buffer is not None or self._clip_buffer is not None
            if need_hires:
                jpeg_hires = encode_frame(frame, self._evidence_tier)
                f_hires = Frame(camera_id=self.camera_id, data=jpeg_hires, width=w, height=h)
                if self._hires_buffer is not None:
                    self._hires_buffer.put(f_hires)
                if self._clip_buffer is not None:
                    self._clip_buffer.put(f_hires)

            # Stream tier → MJPEG stream buffer (separate from AI + evidence)
            if self._stream_buffer is not None:
                if self._stream_tier == self._evidence_tier and need_hires:
                    # Reuse already-encoded evidence frame if tiers match
                    self._stream_buffer.put(f_hires)  # type: ignore[possibly-undefined]
                else:
                    jpeg_stream = encode_frame(frame, self._stream_tier)
                    self._stream_buffer.put(
                        Frame(camera_id=self.camera_id, data=jpeg_stream, width=w, height=h)
                    )

            # Compute rolling FPS via exponential moving average
            now = time.monotonic()
            if self._fps_last_time > 0:
                interval = now - self._fps_last_time
                instant_fps = 1.0 / interval if interval > 0 else 0.0
                # EMA alpha=0.2 → smooth over ~5 frames
                self._fps_ema = 0.2 * instant_fps + 0.8 * self._fps_ema
            self._fps_last_time = now

            msg = MTPMessage(
                msg_type=MTPMsgType.FRAME_READY,
                payload={
                    "camera_id": self.camera_id,
                    "width": w,
                    "height": h,
                    "fps": round(self._fps_ema, 1),
                },
                priority=MTPPriority.NORMAL,
                source=f"cam-{self.camera_id}",
                ttl_seconds=1.0,
            )
            self._bus.publish_nowait(msg)
        except Exception:
            logger.exception("Camera %d frame processing error", self.camera_id)

    def _handle_failure(
        self, attempt: int, cap: cv2.VideoCapture, backoff: list[int]
    ) -> None:
        cap.release()
        wait = backoff[min(attempt, len(backoff) - 1)]
        logger.warning(
            "Camera %d connection failed (attempt %d/%d) — retry in %ds [%s]",
            self.camera_id, attempt + 1, _MAX_RETRIES, wait, self._source_label(),
        )
        err = f"Attempt {attempt + 1}/{_MAX_RETRIES} — retry in {wait}s"
        self._state.update_camera_meta(
            self.camera_id,
            error_msg=err,
            reconnect_attempts=attempt + 1,
        )
        self._publish_status("connecting", error_msg=err)
        msg = MTPMessage(
            msg_type=MTPMsgType.CAMERA_RECONNECT,
            payload=CameraReconnectPayload(
                camera_id=self.camera_id,
                attempt=attempt + 1,
                backoff_seconds=wait,
            ).model_dump(),
            priority=MTPPriority.HIGH,
            source=f"cam-{self.camera_id}",
        )
        self._bus.publish_nowait(msg)
        self._stop_event.wait(timeout=wait)

    def _publish_status(self, status: str, error_msg: str | None = None) -> None:
        try:
            msg = MTPMessage(
                msg_type=MTPMsgType.CAMERA_STATUS,
                payload=CameraStatusPayload(
                    camera_id=self.camera_id,
                    status=status,
                    error_msg=error_msg,
                ).model_dump(),
                priority=MTPPriority.HIGH,
                source=f"cam-{self.camera_id}",
            )
            self._bus.publish_nowait(msg)
        except Exception:
            pass
