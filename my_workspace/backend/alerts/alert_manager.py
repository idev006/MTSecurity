"""AlertManager — subscribe RULE_TRIGGERED, persist event, dispatch notifications."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from alerts.notifications.base import AlertPayload
from protocol.mtp import MTPMessage, MTPMsgType, MTPPriority
from protocol.payloads import AlertFiredPayload

if TYPE_CHECKING:
    from alerts.notifications.dispatcher import NotificationDispatcher
    from protocol.message_bus import MessageBus
    from ssot.config_service import ConfigService

logger = logging.getLogger(__name__)


class AlertManager:
    """
    Subscribes to RULE_TRIGGERED:
      1. Persists an Event row to DB
      2. Saves snapshot (if frame available)
      3. Dispatches notifications via NotificationDispatcher
      4. Publishes ALERT_FIRED for WebSocket broadcast

    Cooldown is already enforced by RuleEngine — AlertManager trusts it.
    """

    def __init__(
        self,
        dispatcher: "NotificationDispatcher",
        config_svc: "ConfigService",
        bus: "MessageBus",
        base_url: str,
    ) -> None:
        self._dispatcher = dispatcher
        self._config = config_svc
        self._bus = bus
        self._base_url = base_url.rstrip("/")

    def register(self, bus: "MessageBus") -> None:
        bus.subscribe(MTPMsgType.RULE_TRIGGERED, self._on_rule_triggered)
        bus.subscribe(MTPMsgType.ALERT_ACKNOWLEDGED, self._on_alert_acknowledged)

    async def _on_rule_triggered(self, msg: MTPMessage) -> None:
        p = msg.payload
        rule_name  = p.get("rule_name", "")
        camera_id  = p.get("camera_id", 0)
        behavior   = p.get("behavior", "")
        severity   = p.get("severity", "medium")   # from rule config
        confidence = p.get("confidence", 0.0)
        snapshot_path = p.get("snapshot_path")

        # Resolve camera name
        cam = await self._config.get_camera(camera_id)
        camera_name = cam.name if cam else f"Camera {camera_id}"

        # Build alert payload (event_id is 0 until DB write in Phase 4)
        snapshot_url = (
            f"{self._base_url}/api/v1/events/0/snapshot"
            if snapshot_path else None
        )

        alert = AlertPayload(
            event_id=0,
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

        # Dispatch notifications
        results = await self._dispatcher.dispatch(alert)
        channels_notified = [r.channel for r in results if r.success]

        # Publish ALERT_FIRED for WebSocket
        fired_payload = AlertFiredPayload(
            alert_id=0,
            rule_name=rule_name,
            camera_id=camera_id,
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
            "Alert fired — rule=%s camera=%d severity=%s notified=%s",
            rule_name, camera_id, severity, channels_notified,
        )

    async def _on_alert_acknowledged(self, msg: MTPMessage) -> None:
        p = msg.payload
        logger.info(
            "Alert %d acknowledged by %s", p.get("alert_id"), p.get("acknowledged_by")
        )
