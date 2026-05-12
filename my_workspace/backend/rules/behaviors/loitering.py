"""Loitering behavior — triggers when object stays in zone > threshold seconds."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rules.behaviors.base import RuleBehavior, TriggerResult

if TYPE_CHECKING:
    from ai.tracker import Track
    from rules.dwell_tracker import DwellTracker
    from rules.zone_manager import ZoneManager


class LoiteringBehavior(RuleBehavior):
    name = "loitering"

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
        dwell_threshold = config.get("dwell_threshold_seconds", 30)

        if track.confidence < threshold:
            return TriggerResult.no()

        if not zone_manager.is_inside(zone_id, track.centroid):
            dwell_tracker.exit(rule_id, track.track_id)
            return TriggerResult.no()

        dwell = dwell_tracker.touch(rule_id, track.track_id)

        if dwell >= dwell_threshold:
            return TriggerResult.yes(
                confidence=track.confidence,
                track_id=track.track_id,
                dwell_seconds=round(dwell, 1),
                centroid=track.centroid,
            )
        return TriggerResult.no()
