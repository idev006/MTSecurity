"""AlertManager — subscribe RULE_TRIGGERED, persist event, dispatch notifications."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable

from alerts.notifications.base import AlertPayload
from models.event import Event
from protocol.mtp import MTPMessage, MTPMsgType, MTPPriority
from protocol.payloads import AlertFiredPayload

if TYPE_CHECKING:
    from alerts.notifications.dispatcher import NotificationDispatcher
    from protocol.message_bus import MessageBus
    from ssot.config_service import ConfigService
    from ingestion.frame_buffer import FrameBuffer
    from pathlib import Path

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Subscribes to RULE_TRIGGERED:
      1. Persists an Event row to DB (with real event_id)
      2. Dispatches notifications via NotificationDispatcher
      3. Publishes ALERT_FIRED for WebSocket broadcast

    Cooldown is already enforced by RuleEngine — AlertManager trusts it.
    """

    def __init__(
        self,
        dispatcher: "NotificationDispatcher",
        config_svc: "ConfigService",
        bus: "MessageBus",
        base_url: str,
        session_factory: Callable,
        frame_buffer: "FrameBuffer",
        snapshot_dir: "Path",
    ) -> None:
        self._dispatcher = dispatcher
        self._config = config_svc
        self._bus = bus
        self._base_url = base_url.rstrip("/")
        self._session_factory = session_factory
        self._frame_buffer = frame_buffer
        self._snapshot_dir = snapshot_dir

    def register(self, bus: "MessageBus") -> None:
        bus.subscribe(MTPMsgType.RULE_TRIGGERED, self._on_rule_triggered)
        bus.subscribe(MTPMsgType.ALERT_ACKNOWLEDGED, self._on_alert_acknowledged)

    async def _on_rule_triggered(self, msg: MTPMessage) -> None:
        p = msg.payload
        rule_id    = p.get("rule_id", 0)
        rule_name  = p.get("rule_name", "")
        camera_id  = p.get("camera_id", 0)
        zone_id    = p.get("zone_id")
        behavior   = p.get("behavior", "")
        severity   = p.get("severity", "medium")
        confidence = p.get("confidence", 0.0)
        track_id   = p.get("track_id")
        
        # We don't get snapshot_path from RuleEngine anymore, AlertManager creates it
        snapshot_path = None
        
        # ── 1. Create Event in DB first to get event_id ───────────────────────
        event_id = 0
        async with self._session_factory() as db:
            event = Event(
                camera_id=camera_id,
                rule_id=rule_id if rule_id else None,
                behavior=behavior,
                severity=severity,
                confidence=confidence,
                track_id=track_id,
                occurred_at=datetime.now(timezone.utc),
                status="NEW",
            )
            db.add(event)
            await db.flush()
            event_id = event.id
            
            # ── 2. Capture Snapshot ─────────────────────────────────────────────
            frame = self._frame_buffer.get(camera_id)
            if frame:
                logger.info("AlertManager: Frame found for camera %d. Attempting snapshot capture...", camera_id)
                try:
                    import cv2
                    import numpy as np
                    from alerts.snapshot import save_snapshot
                    
                    # Decode jpeg
                    nparr = np.frombuffer(frame.data, np.uint8)
                    img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if img_np is not None:
                        # Reconstruct detection dict for the annotator
                        detections = []
                        meta = p.get("metadata", {})
                        if "bbox" in meta:
                            detections.append({
                                "track_id": track_id,
                                "label": meta.get("label", "unknown"),
                                "confidence": confidence,
                                "bbox": meta["bbox"],
                            })
                        
                        path = save_snapshot(
                            frame=img_np,
                            detections=detections,
                            rule_name=rule_name,
                            severity=severity,
                            snapshot_dir=self._snapshot_dir,
                            camera_id=camera_id,
                            event_id=event_id,
                        )
                        # Save relative path to db (e.g. filename only)
                        event.snapshot_path = path.name
                        snapshot_path = path.name
                        logger.info("AlertManager: Snapshot saved to %s", path)
                    else:
                        logger.error("AlertManager: Failed to decode frame for camera %d", camera_id)
                except Exception as e:
                    logger.error("AlertManager: Failed to capture snapshot for event %d: %s", event_id, e, exc_info=True)
            else:
                logger.warning("AlertManager: No frame found in buffer for camera %d. Buffer keys: %s",
                               camera_id, list(self._frame_buffer._slots.keys()))
            
            await db.commit()
            logger.info("Event %d persisted — behavior=%s camera=%d snapshot=%s", event_id, behavior, camera_id, snapshot_path)

        # ── 3. Resolve camera name ────────────────────────────────────────────
        cam = await self._config.get_camera(camera_id)
        camera_name = cam.name if cam else f"Camera {camera_id}"

        snapshot_url = (
            f"{self._base_url}/api/v1/events/{event_id}/snapshot"
            if snapshot_path else None
        )

        # ── 3. Dispatch notifications ────────────────────────────────────────
        alert = AlertPayload(
            event_id=event_id,
            rule_name=rule_name,
            camera_id=camera_id,
            camera_name=camera_name,
            behavior=behavior,
            severity=severity,
            confidence=confidence,
            snapshot_url=snapshot_url,
            clip_url=None,
            occurred_at=datetime.now(timezone.utc).isoformat(),
        )
        results = await self._dispatcher.dispatch(alert)
        channels_notified = [r.channel for r in results if r.success]

        # ── 4. Publish ALERT_FIRED for WebSocket ──────────────────────────────
        fired_payload = AlertFiredPayload(
            alert_id=event_id,
            rule_name=rule_name,
            camera_id=camera_id,
            behavior=behavior,
            severity=severity,
            snapshot_url=snapshot_url,
            clip_url=None,
            channels_notified=channels_notified,
        )
        fired_msg = MTPMessage(
            msg_type=MTPMsgType.ALERT_FIRED,
            payload=fired_payload.model_dump(),
            priority=MTPPriority.HIGH,
            source="alert-manager",
        )
        await self._bus.publish(fired_msg)

        logger.info(
            "Alert fired — event=%d rule=%s camera=%d severity=%s",
            event_id, rule_name, camera_id, severity,
        )

    async def _on_alert_acknowledged(self, msg: MTPMessage) -> None:
        p = msg.payload
        logger.info(
            "Alert %d acknowledged by %s", p.get("alert_id"), p.get("acknowledged_by")
        )
