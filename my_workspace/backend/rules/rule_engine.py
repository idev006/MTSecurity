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

        # Admin-configurable defaults (live-reload via CONFIG_CHANGED)
        self._default_cooldown: int = 60        # seconds
        self._default_confidence: float = 0.6   # 0.0–1.0

        # BUG-019: track last-seen time to expire cooldowns for dead tracks
        # key: track_id → monotonic time of last detection
        self._track_last_seen: dict[int, float] = {}
        # seconds without detection before a track's cooldown entries are cleared
        self._stale_track_seconds: float = 3.0

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

        # BUG-019: update last-seen time for every active track, then expire stale cooldowns
        now = time.monotonic()
        for det in detections:
            tid = det.get("track_id")
            if tid is not None:
                self._track_last_seen[tid] = now
        self._expire_stale_cooldowns(now)

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

                logger.debug("Track %d centroid=(%.3f, %.3f) zone=%d inside=%s",
                             det.get("track_id"), cx, cy, zone_id, inside)

        for det in detections:
            track_id = det.get("track_id")
            cx = (det["bbox"]["x1"] + det["bbox"]["x2"]) / 2
            cy = (det["bbox"]["y1"] + det["bbox"]["y2"]) / 2

            for rule_id, rule_cfg in self._rules.items():
                if rule_cfg.get("camera_id") != camera_id:
                    continue
                if not rule_cfg.get("zone_is_active", True):
                    continue
                if not rule_cfg.get("is_active", True):
                    continue

                # BUG-020: apply per-rule confidence threshold (fallback to global default)
                conf_threshold = rule_cfg.get("confidence_threshold") or self._default_confidence
                if det.get("confidence", 0.0) < conf_threshold:
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
                    cooldown = rule_cfg.get("cooldown_seconds") or self._default_cooldown
                    if self._is_in_cooldown(rule_id, track.track_id, cooldown):
                        logger.info("Rule %d evaluation: SUPPRESSED (cooldown)", rule_id)
                        continue
                    self._set_cooldown(rule_id, track.track_id)

                    # When Advanced Logic is used, rule.behavior may not match
                    # the behavior node inside the logic tree (common when the user
                    # didn't update the top-level behavior field after editing the
                    # logic tree).  Extract the actual behavior type from the tree
                    # so the alert reflects what really fired.
                    behavior_override = _extract_behavior_from_tree(
                        logic_tree, rule_cfg.get("behavior", "")
                    )

                    from rules.behaviors.base import TriggerResult
                    meta = {"label": track.label, "bbox": track.bbox}
                    result = TriggerResult(triggered=True, confidence=track.confidence, metadata=meta)
                    await self._emit_triggered(
                        rule_id, rule_cfg, camera_id, rule_cfg["zone_id"],
                        track, result, behavior_override=behavior_override,
                    )
                else:
                    # Optional: log why it failed
                    pass

    async def _on_config_changed(self, msg: MTPMessage) -> None:
        scope = msg.payload.get("scope")
        entity_id = msg.payload.get("entity_id")

        # FEAT-011: live-reload admin-configurable detection defaults
        if scope == "system_setting":
            key = msg.payload.get("key")
            value = msg.payload.get("value", "")
            if key == "default_cooldown_seconds":
                self._default_cooldown = int(value)
                logger.info("RuleEngine: default_cooldown_seconds → %s s", value)
            elif key == "default_confidence_threshold":
                self._default_confidence = int(value) / 100.0
                logger.info("RuleEngine: default_confidence_threshold → %s%%", value)
            return

        if scope == "rule":
            rule = await self._config.get_rule(entity_id)
            if rule:
                await self._cache_rule(rule)
            else:
                self._rules.pop(entity_id, None)

        elif scope == "zone":
            zone = await self._config.get_zone(entity_id)
            if zone:
                self._zone_mgr.update_zone(zone.id, zone.coordinates)
                for rule_cfg in self._rules.values():
                    if rule_cfg["zone_id"] == entity_id:
                        rule_cfg["zone_is_active"] = zone.is_active
            else:
                # Zone deleted — remove all rules that belonged to it
                dead = [rid for rid, r in self._rules.items() if r["zone_id"] == entity_id]
                for rid in dead:
                    self._rules.pop(rid, None)

        elif scope == "camera":
            # Camera deleted — remove all rules whose camera_id matches
            dead = [rid for rid, r in self._rules.items() if r.get("camera_id") == entity_id]
            for rid in dead:
                self._rules.pop(rid, None)

    # ── Helpers ───────────────────────────────────────────────────────────────

    async def _cache_rule(self, rule) -> None:
        zone = await self._config.get_zone(rule.zone_id)
        if zone is None:
            logger.warning("RuleEngine: zone %d not found for rule %d — skipping", rule.zone_id, rule.id)
            self._rules.pop(rule.id, None)
            return
        camera_id = zone.camera_id

        self._rules[rule.id] = {
            "rule_id": rule.id,
            "zone_id": rule.zone_id,
            "camera_id": camera_id,
            "behavior": rule.behavior,
            "is_active": rule.is_active,
            "zone_is_active": zone.is_active,
            "confidence_threshold": rule.confidence_threshold,
            "dwell_threshold_seconds": rule.dwell_threshold_seconds,
            "cooldown_seconds": rule.cooldown_seconds,
            "severity": rule.severity,
            "name": rule.name,
            "logic": json.loads(rule.logic) if rule.logic else None,
            "behavior_params": json.loads(rule.behavior_params) if rule.behavior_params else {},
        }
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

    def _expire_stale_cooldowns(self, now: float) -> None:
        """BUG-019: clear cooldown entries for track_ids that have not been seen recently.

        When a tracker reuses an old track_id for a new object, the new object
        would inherit the previous cooldown and be suppressed. Expiring the entry
        once the original track has been gone for _stale_track_seconds prevents
        the false suppression.
        """
        stale_ids = {
            tid for tid, last_seen in self._track_last_seen.items()
            if (now - last_seen) > self._stale_track_seconds
        }
        if not stale_ids:
            return
        dead_keys = [k for k in self._last_trigger if k[1] in stale_ids]
        for k in dead_keys:
            del self._last_trigger[k]
        for tid in stale_ids:
            del self._track_last_seen[tid]
        if dead_keys:
            logger.debug("Expired %d cooldown(s) for stale track(s): %s", len(dead_keys), stale_ids)

    async def _emit_triggered(
        self, rule_id, rule_cfg, camera_id, zone_id, track, result,
        behavior_override: str | None = None,
    ) -> None:
        behavior = behavior_override or rule_cfg.get("behavior", "")
        payload = RuleTriggeredPayload(
            rule_id=rule_id,
            rule_name=rule_cfg.get("name", ""),
            camera_id=camera_id,
            zone_id=zone_id,
            track_id=track.track_id,
            behavior=behavior,
            confidence=result.confidence,
            severity=rule_cfg.get("severity", "medium"),
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
            rule_id, behavior, camera_id, track.track_id, result.confidence,
        )

    def update_zone_cache(self, zone_id: int, coords_json: str) -> None:
        self._zone_mgr.update_zone(zone_id, coords_json)


def _extract_behavior_from_tree(node: dict | None, fallback: str) -> str:
    """Walk a logic tree and return the first behavior node's type.

    When Advanced Logic is used, the top-level ``rule.behavior`` field may not
    reflect the actual behavior configured in the tree (common when the form
    defaulted to 'intrusion' before the user switched to the logic builder).
    This helper extracts the real type so alerts report correctly.
    """
    if not node:
        return fallback
    # Leaf node — behavior condition
    if node.get("type") == "behavior":
        return node.get("params", {}).get("type", fallback)
    # Operator node — recurse into children
    for child in node.get("conditions", []):
        found = _extract_behavior_from_tree(child, fallback)
        if found != fallback:
            return found
    return fallback


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
