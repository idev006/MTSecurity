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
from rules.logic_validator import LogicValidator
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
        self._logic_validator = LogicValidator(self._zone_mgr, self._schedule_mgr, self._dwell)

        # rule_id → rule config dict (cached from DB)
        self._rules: dict[int, dict[str, Any]] = {}
        # Cooldown: (rule_id, track_id) → last trigger monotonic time
        self._last_trigger: dict[tuple[int, int], float] = {}

    async def initialize(self) -> None:
        """Load all active rules and zones into memory."""
        logger.info("RuleEngine: starting initialization...")
        rules = await self._config.get_active_rules()
        logger.info("RuleEngine: found %d active rules in DB", len(rules))
        for rule in rules:
            await self._cache_rule(rule)
        logger.info("RuleEngine: initialization complete. Cached rules: %s", list(self._rules.keys()))

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
                inside = self._zone_mgr.is_inside(zone_id, (cx, cy))
                if inside:
                    zone_counts[zone_id] = zone_counts.get(zone_id, 0) + 1
                
                # Use INFO so it shows up without DEBUG=true
                logger.info("Track %d centroid=(%.3f, %.3f) zone=%d inside=%s", 
                             det.get("track_id"), cx, cy, zone_id, inside)

        for det in detections:
            track_id = det.get("track_id")
            cx = (det["bbox"]["x1"] + det["bbox"]["x2"]) / 2
            cy = (det["bbox"]["y1"] + det["bbox"]["y2"]) / 2

            for rule_id, rule_cfg in self._rules.items():
                if rule_cfg.get("camera_id") != camera_id:
                    continue
                if not rule_cfg.get("is_active", True):
                    continue
                
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

                # NEW: Use LogicValidator for full condition evaluation
                context = {
                    "track": track,
                    "rule_id": rule_id,
                    "rule_cfg": rule_cfg,
                    "zone_id": rule_cfg["zone_id"],
                    "zone_count": zone_counts.get(rule_cfg["zone_id"], 0)
                }

                logic_tree = rule_cfg.get("logic")
                triggered = self._logic_validator.evaluate(logic_tree, context)

                if triggered:
                    logger.info("Rule %d evaluation: TRIGGERED (track=%d)", rule_id, track.track_id)
                    if self._is_in_cooldown(rule_id, track.track_id, rule_cfg.get("cooldown_seconds", 60)):
                        logger.info("Rule %d evaluation: SUPPRESSED (cooldown)", rule_id)
                        continue
                    self._set_cooldown(rule_id, track.track_id)
                    
                    # For emit, we still need a 'result' object for compatibility
                    from rules.behaviors.base import TriggerResult
                    # Pass the label and bbox in metadata for the snapshot annotator
                    meta = {
                        "label": track.label,
                        "bbox": track.bbox
                    }
                    result = TriggerResult(triggered=True, confidence=track.confidence, metadata=meta)
                    await self._emit_triggered(rule_id, rule_cfg, camera_id, rule_cfg["zone_id"], track, result)
                else:
                    # Optional: log why it failed
                    pass

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

    async def _cache_rule(self, rule) -> None:
        zone = await self._config.get_zone(rule.zone_id)
        camera_id = zone.camera_id if zone else None

        self._rules[rule.id] = {
            "rule_id": rule.id,
            "zone_id": rule.zone_id,
            "camera_id": camera_id,
            "behavior": rule.behavior,
            "is_active": rule.is_active,
            "confidence_threshold": rule.confidence_threshold,
            "dwell_threshold_seconds": rule.dwell_threshold_seconds,
            "cooldown_seconds": rule.cooldown_seconds,
            "severity": rule.severity,
            "name": rule.name,
            "logic": json.loads(rule.logic) if rule.logic else None,
        }
        if zone:
            self._zone_mgr.update_zone(zone.id, zone.coordinates)
        self._schedule_mgr.update(rule.id, rule.schedule)

    def _get_camera_id_for_zone(self, zone_id: int) -> int | None:
        # Deprecated: camera_id now cached directly in _rules during _cache_rule
        for r in self._rules.values():
            if r["zone_id"] == zone_id:
                return r["camera_id"]
        return None

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
        return {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2}
