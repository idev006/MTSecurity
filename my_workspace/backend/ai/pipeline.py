"""AIPipeline — round-robin AI processing loop with WIP=2 concurrency limit."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import numpy as np

from ai.detector import Detection, postprocess_yolo
from ai.session_registry import SessionRegistry
from ai.tracker import ObjectTracker
from ingestion.frame_buffer import FrameBuffer
from ingestion.frame_codec import frame_to_rgb, resize_for_inference
from protocol.mtp import MTPMessage, MTPMsgType, MTPPriority
from protocol.payloads import TrackUpdatePayload

if TYPE_CHECKING:
    from ai.inference_engine import InferenceEngine
    from protocol.message_bus import MessageBus

logger = logging.getLogger(__name__)

_WIP_LIMIT = 2          # max concurrent inference tasks
_POLL_INTERVAL = 0.033  # ~30 Hz round-robin poll (actual fps throttled per camera)


class AIPipeline:
    """
    Single background thread that round-robins through cameras in FrameBuffer.

    Concurrency:
      - _WIP semaphore limits simultaneous inferences to 2
      - Each inference runs in a ThreadPoolExecutor (blocking OpenVINO call)
      - Results dispatched as TRACK_UPDATE on the bus

    Graceful degradation:
      - If InferenceEngine not ready (no model file), emits empty TRACK_UPDATE
      - Inference errors are logged, not propagated
    """

    def __init__(
        self,
        buffer: FrameBuffer,
        engine: "InferenceEngine",
        bus: "MessageBus",
        confidence_threshold: float = 0.6,
        target_classes: list[int] | None = None,
    ) -> None:
        self._buffer = buffer
        self._engine = engine
        self._bus = bus
        self._confidence = confidence_threshold
        self._target_classes = target_classes  # None = all COCO classes
        self._trackers: dict[int, ObjectTracker] = {}
        self._trackers_lock = threading.Lock()
        self._processing: set[int] = set()   # cameras with in-flight inference
        self._session_reg = SessionRegistry()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        # loop parameter kept for API compatibility but no longer used directly —
        # publish_nowait() captures it from the bus at bus.start() time.
        self._thread = threading.Thread(target=self._run, name="ai-pipeline", daemon=True)
        self._thread.start()
        logger.info("AIPipeline started (WIP=%d, classes=%s)", _WIP_LIMIT, self._target_classes)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    # ── Main loop ─────────────────────────────────────────────────────────────

    def _run(self) -> None:
        semaphore = threading.Semaphore(_WIP_LIMIT)

        while not self._stop_event.is_set():
            camera_ids = self._buffer.active_camera_ids()
            if not camera_ids:
                time.sleep(_POLL_INTERVAL)
                continue

            for camera_id in camera_ids:
                if self._stop_event.is_set():
                    break

                frame = self._buffer.get(camera_id)
                if frame is None:
                    continue

                # Acquire WIP slot (blocks if 2 already running)
                if not semaphore.acquire(timeout=0.1):
                    continue

                with self._trackers_lock:
                    if camera_id in self._processing:
                        semaphore.release()
                        continue
                    self._processing.add(camera_id)

                def process(cam_id=camera_id, f=frame, sem=semaphore):
                    try:
                        self._process_frame(cam_id, f)
                    finally:
                        with self._trackers_lock:
                            self._processing.discard(cam_id)
                        sem.release()

                t = threading.Thread(target=process, daemon=True)
                t.start()

            time.sleep(_POLL_INTERVAL)

    def _process_frame(self, camera_id: int, frame) -> None:
        try:
            # Decode JPEG → RGB ndarray
            from ingestion.frame_codec import decode_frame
            bgr = decode_frame(frame.data)
            rgb = frame_to_rgb(bgr)

            # Letterbox + inference
            blob, scale, pad_top, pad_left = resize_for_inference(rgb, 640)
            outputs, elapsed_ms = self._engine.infer(blob)

            # Postprocess
            detections = postprocess_yolo(
                outputs,
                orig_w=rgb.shape[1],
                orig_h=rgb.shape[0],
                pad_top=pad_top,
                pad_left=pad_left,
                scale=scale,
                confidence_threshold=self._confidence,
                target_classes=self._target_classes,
            ) if outputs else []

            # Track
            with self._trackers_lock:
                if camera_id not in self._trackers:
                    self._trackers[camera_id] = ObjectTracker()
                tracker = self._trackers[camera_id]
            tracks = tracker.update(detections)

            # Update session registry
            active_ids = {t.track_id for t in tracks}
            for track in tracks:
                self._session_reg.register(track.track_id, camera_id)
            for old_id in self._session_reg.active_tracks(camera_id):
                if old_id not in active_ids:
                    self._session_reg.remove_track(old_id)

            # Publish TRACK_UPDATE
            self._emit_track_update(camera_id, tracks, frame.captured_at, elapsed_ms)

        except Exception:
            logger.exception("AIPipeline error on camera %d", camera_id)

    def _emit_track_update(self, camera_id: int, tracks, captured_at, elapsed_ms: float) -> None:
        from protocol.payloads import BoundingBox, Detection as PayloadDetection, TrackUpdatePayload

        payload_detections = [
            PayloadDetection(
                label=t.label,
                confidence=t.confidence,
                bbox=BoundingBox(x1=t.x1, y1=t.y1, x2=t.x2, y2=t.y2),
                track_id=t.track_id,
            )
            for t in tracks
        ]

        msg = MTPMessage(
            msg_type=MTPMsgType.TRACK_UPDATE,
            payload=TrackUpdatePayload(
                camera_id=camera_id,
                detections=payload_detections,
                frame_timestamp=captured_at,
            ).model_dump(mode="json"),
            priority=MTPPriority.NORMAL,
            source="ai-pipeline",
        )

        # publish_nowait is thread-safe (routes through call_soon_threadsafe internally)
        # Prefer it over run_coroutine_threadsafe so we never block the thread pool
        # and never leave dangling futures that pile up if the queue backs up.
        self._bus.publish_nowait(msg)

    @property
    def session_registry(self) -> SessionRegistry:
        return self._session_reg
