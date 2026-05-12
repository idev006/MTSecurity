"""Intrusion behavior — triggers when object enters restricted zone."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rules.behaviors.base import RuleBehavior, TriggerResult

if TYPE_CHECKING:
    from ai.tracker import Track
    from rules.dwell_tracker import DwellTracker
    from rules.zone_manager import ZoneManager


class IntrusionBehavior(RuleBehavior):
    """
    Fires on the FIRST frame an object enters the zone.
    Subsequent frames while still inside are suppressed (cooldown handles repeats).
    """

    name = "intrusion"

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
        if track.confidence < threshold:
            return TriggerResult.no()

        if not zone_manager.is_inside(zone_id, track.centroid):
            dwell_tracker.exit(rule_id, track.track_id)
            return TriggerResult.no()

        already_inside = dwell_tracker.has_entry(rule_id, track.track_id)
        dwell_tracker.enter(rule_id, track.track_id)

        if not already_inside:
            return TriggerResult.yes(
                confidence=track.confidence,
                track_id=track.track_id,
                centroid=track.centroid,
                bbox=track.bbox,
            )
        return TriggerResult.no()
