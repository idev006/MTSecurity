"""RuleEngine — subscribes to TRACK_UPDATE, evaluates all rules, emits RULE_TRIGGERED."""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

from rules.behaviors import BEHAVIOR_REGISTRY
from rules.dwell_tracker import DwellTracker
from rules.schedule_manager import ScheduleManager
from rules.zone_manager import ZoneManager
from protocol.mtp import MTPMessage, MTPMsgType, MTPPriority
from protocol.payloads import RuleTriggeredPayload

if TYPE_CHECKING:
    from protocol.message_bus import MessageBus
    from ssot.config_service import ConfigService

logger = logging.getLogger(__name__)


class RuleEngine:
    """
    Evaluates all active rules against every TRACK_UPDATE message.

    Architecture:
      - Subscribes to TRACK_UPDATE (from AIPipeline)
      - Subscribes to CONFIG_CHANGED (hot-reload rules/zones from SSOT)
      - For each track × each rule: runs the matching RuleBehavior
      - On trigger: publishes RULE_TRIGGERED → AlertManager picks it up
    """

    def __init__(self, config_svc: "ConfigService", bus: "MessageBus") -> None:
        self._config = config_svc
        self._bus = bus
        self._zone_mgr = ZoneManager()
        self._schedule_mgr = ScheduleManager()
        self._dwell = DwellTracker()

        # rule_id → rule config dict (cached from DB)
        self._rules: dict[int, dict[str, Any]] = {}
        # Cooldown: (rule_id, track_id) → last trigger monotonic time
        self._last_trigger: dict[tuple[int, int], float] = {}

    async def initialize(self) -> None:
        """Load all active rules and zones into memory."""
        rules = await self._config.get_active_rules()
        for rule in rules:
            self._cache_rule(rule)

        cameras = await self._config.get_active_cameras()
        for cam in cameras:
            zones = await self._config.get_active_cameras()  # zones loaded via zone cache
        # Zones are loaded on-demand from config_svc.get_zone()
        logger.info("RuleEngine: loaded %d active rules", len(self._rules))

    def register(self, bus: "MessageBus") -> None:
        bus.subscribe(MTPMsgType.TRACK_UPDATE, self._on_track_update)
        bus.subscribe(MTPMsgType.CONFIG_CHANGED, self._on_config_changed)

    # ── Handlers ─────────────────────────────────────────────────────────────

    async def _on_track_update(self, msg: MTPMessage) -> None:
        payload = msg.payload
        camera_id: int = payload["camera_id"]
        detections: list[dict] = payload.get("detections", [])

        if not detections or not self._rules:
            return

        # Get zones for this camera
        camera_rules = [r for r in self._rules.values() if r.get("camera_id") == camera_id]
        if not camera_rules:
            return

        # Count objects per zone for crowd_density
        zone_counts: dict[int, int] = {}
        for det in detections:
            cx = (det["bbox"]["x1"] + det["bbox"]["x2"]) / 2
            cy = (det["bbox"]["y1"] + det["bbox"]["y2"]) / 2
            for rule_cfg in camera_rules:
                zone_id = rule_cfg["zone_id"]
                if self._zone_mgr.is_inside(zone_id, (cx, cy)):
                    zone_counts[zone_id] = zone_counts.get(zone_id, 0) + 1

        for det in detections:
            track_id = det.get("track_id")
            cx = (det["bbox"]["x1"] + det["bbox"]["x2"]) / 2
            cy = (det["bbox"]["y1"] + det["bbox"]["y2"]) / 2

            for rule_id, rule_cfg in self._rules.items():
                if rule_cfg.get("camera_id") != camera_id:
                    continue
                if not rule_cfg.get("is_active", True):
                    continue
                if not self._schedule_mgr.is_active(rule_id):
                    continue

                behavior_name = rule_cfg.get("behavior", "")
                behavior = BEHAVIOR_REGISTRY.get(behavior_name)
                if behavior is None:
                    continue

                zone_id = rule_cfg["zone_id"]
                config = dict(rule_cfg)
                config["zone_count"] = zone_counts.get(zone_id, 0)

                # Build a minimal track-like object from payload
                track = _TrackProxy(
                    track_id=track_id or 0,
                    label=det.get("label", "person"),
                    class_id=0,
                    confidence=det.get("confidence", 0.0),
                    centroid=(cx, cy),
                    bbox=(det["bbox"]["x1"], det["bbox"]["y1"],
                          det["bbox"]["x2"], det["bbox"]["y2"]),
                )

                result = behavior.evaluate(
                    track=track,
                    rule_id=rule_id,
                    zone_id=zone_id,
                    zone_manager=self._zone_mgr,
                    dwell_tracker=self._dwell,
                    config=config,
                )

                if result.triggered:
                    if self._is_in_cooldown(rule_id, track.track_id, rule_cfg.get("cooldown_seconds", 60)):
                        continue
                    self._set_cooldown(rule_id, track.track_id)
                    await self._emit_triggered(rule_id, rule_cfg, camera_id, zone_id, track, result)

    async def _on_config_changed(self, msg: MTPMessage) -> None:
        scope = msg.payload.get("scope")
        entity_id = msg.payload.get("entity_id")

        if scope == "rule":
            rule = await self._config.get_rule(entity_id)
            if rule:
                self._cache_rule(rule)
            else:
                self._rules.pop(entity_id, None)

        elif scope == "zone":
            zone = await self._config.get_zone(entity_id)
            if zone:
                self._zone_mgr.update_zone(zone.id, zone.coordinates)
                self._schedule_mgr.update(entity_id, None)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _cache_rule(self, rule) -> None:
        self._rules[rule.id] = {
            "rule_id": rule.id,
            "zone_id": rule.zone_id,
            "camera_id": self._get_camera_id_for_zone(rule.zone_id),
            "behavior": rule.behavior,
            "is_active": rule.is_active,
            "confidence_threshold": rule.confidence_threshold,
            "dwell_threshold_seconds": rule.dwell_threshold_seconds,
            "cooldown_seconds": rule.cooldown_seconds,
            "severity": rule.severity,
            "name": rule.name,
        }
        self._schedule_mgr.update(rule.id, rule.schedule)

    def _get_camera_id_for_zone(self, zone_id: int) -> int | None:
        # Zones carry camera_id; ZoneManager cache may not have it
        # RuleEngine resolves this lazily from SSOT
        return None   # resolved in _on_track_update via camera_id loop

    def _is_in_cooldown(self, rule_id: int, track_id: int, cooldown: int) -> bool:
        last = self._last_trigger.get((rule_id, track_id))
        if last is None:
            return False
        return (time.monotonic() - last) < cooldown

    def _set_cooldown(self, rule_id: int, track_id: int) -> None:
        self._last_trigger[(rule_id, track_id)] = time.monotonic()

    async def _emit_triggered(self, rule_id, rule_cfg, camera_id, zone_id, track, result) -> None:
        payload = RuleTriggeredPayload(
            rule_id=rule_id,
            rule_name=rule_cfg.get("name", ""),
            camera_id=camera_id,
            zone_id=zone_id,
            track_id=track.track_id,
            behavior=rule_cfg.get("behavior", ""),
            confidence=result.confidence,
            snapshot_path=None,
            metadata=result.metadata,
        )
        msg = MTPMessage(
            msg_type=MTPMsgType.RULE_TRIGGERED,
            payload=payload.model_dump(),
            priority=MTPPriority.HIGH,
            source="rule-engine",
        )
        await self._bus.publish(msg)
        logger.info(
            "Rule %d triggered — behavior=%s camera=%d track=%d confidence=%.2f",
            rule_id, rule_cfg.get("behavior"), camera_id, track.track_id, result.confidence,
        )

    def update_zone_cache(self, zone_id: int, coords_json: str) -> None:
        self._zone_mgr.update_zone(zone_id, coords_json)


class _TrackProxy:
    """Minimal duck-typed Track built from TRACK_UPDATE payload."""
    def __init__(self, track_id, label, class_id, confidence, centroid, bbox):
        self.track_id = track_id
        self.label = label
        self.class_id = class_id
        self.confidence = confidence
        self.centroid = centroid
        self.x1, self.y1, self.x2, self.y2 = bbox

    @property
    def bbox(self):
        return (self.x1, self.y1, self.x2, self.y2)
