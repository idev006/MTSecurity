"""AbandonedObject behavior — triggers when an object stays still for too long."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rules.behaviors.base import RuleBehavior, TriggerResult
from rules.zone_manager import Point

if TYPE_CHECKING:
    from ai.tracker import Track
    from rules.dwell_tracker import DwellTracker
    from rules.zone_manager import ZoneManager


_MOVEMENT_THRESHOLD = 0.02   # normalised coordinate units (2% of frame)


class AbandonedObjectBehavior(RuleBehavior):
    """
    Fires when a stationary object (centroid barely moves) stays in zone
    beyond dwell_threshold_seconds. Useful for detecting bags, packages, etc.
    """

    name = "abandoned_object"

    def __init__(self) -> None:
        self._anchors: dict[tuple[int, int], Point] = {}

    def evaluate(
        self,
        track: "Track",
        rule_id: int,
        zone_id: int,
        zone_manager: "ZoneManager",
        dwell_tracker: "DwellTracker",
        config: dict[str, Any],
    ) -> TriggerResult:
        threshold = config.get("confidence_threshold", 0.6)
        dwell_threshold = config.get("dwell_threshold_seconds", 60)
        move_thresh = config.get("movement_threshold", _MOVEMENT_THRESHOLD)

        if track.confidence < threshold:
            return TriggerResult.no()

        if not zone_manager.is_inside(zone_id, track.centroid):
            self._anchors.pop((rule_id, track.track_id), None)
            dwell_tracker.exit(rule_id, track.track_id)
            return TriggerResult.no()

        key = (rule_id, track.track_id)
        cx, cy = track.centroid

        if key not in self._anchors:
            self._anchors[key] = (cx, cy)
            dwell_tracker.enter(rule_id, track.track_id)
            return TriggerResult.no()

        ax, ay = self._anchors[key]
        dist = ((cx - ax) ** 2 + (cy - ay) ** 2) ** 0.5

        if dist > move_thresh:
            # Object moved — reset anchor and dwell
            self._anchors[key] = (cx, cy)
            dwell_tracker.exit(rule_id, track.track_id)
            dwell_tracker.enter(rule_id, track.track_id)
            return TriggerResult.no()

        dwell = dwell_tracker.touch(rule_id, track.track_id)
        if dwell >= dwell_threshold:
            return TriggerResult.yes(
                confidence=track.confidence,
                track_id=track.track_id,
                dwell_seconds=round(dwell, 1),
                stationary_at=track.centroid,
            )
        return TriggerResult.no()
