"""MQTT notification channel — publishes to mtsecurity/alerts topic."""

from __future__ import annotations

import json
import logging

from alerts.notifications.base import AlertPayload, NotificationChannel, SendResult

logger = logging.getLogger(__name__)

_TOPIC = "mtsecurity/alerts"


class MQTTChannel(NotificationChannel):
    channel_name = "mqtt"

    def __init__(self, broker: str, port: int = 1883, topic: str = _TOPIC) -> None:
        self._broker = broker
        self._port = port
        self._topic = topic

    async def send(self, payload: AlertPayload) -> SendResult:
        try:
            import paho.mqtt.publish as publish
            msg = json.dumps({
                "event_id": payload.event_id,
                "rule_name": payload.rule_name,
                "camera_id": payload.camera_id,
                "severity": payload.severity,
                "behavior": payload.behavior,
                "confidence": payload.confidence,
                "occurred_at": payload.occurred_at,
            })
            publish.single(
                topic=self._topic,
                payload=msg,
                hostname=self._broker,
                port=self._port,
                qos=1,
            )
            return self._result(True)
        except Exception as e:
            logger.error("MQTT publish failed: %s", e)
            return self._result(False, str(e))
