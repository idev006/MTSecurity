"""LineCrossing behavior — triggers when object crosses a defined line."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rules.behaviors.base import RuleBehavior, TriggerResult
from rules.zone_manager import line_crossing_direction

if TYPE_CHECKING:
    from ai.tracker import Track
    from rules.dwell_tracker import DwellTracker
    from rules.zone_manager import ZoneManager


class LineCrossingBehavior(RuleBehavior):
    """
    The zone is treated as a polyline (first two vertices define the crossing line).
    Triggers whenever the track centroid crosses it in either direction.
    """

    name = "line_crossing"

    def __init__(self) -> None:
        self._prev_centroids: dict[tuple[int, int], tuple[float, float]] = {}

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

        polygon = zone_manager.get_polygon(zone_id)
        if not polygon or len(polygon) < 2:
            return TriggerResult.no()

        line_start, line_end = polygon[0], polygon[1]
        key = (rule_id, track.track_id)
        curr = track.centroid

        if key not in self._prev_centroids:
            self._prev_centroids[key] = curr
            return TriggerResult.no()

        prev = self._prev_centroids[key]
        self._prev_centroids[key] = curr

        direction = line_crossing_direction(prev, curr, line_start, line_end)
        if direction != 0:
            return TriggerResult.yes(
                confidence=track.confidence,
                track_id=track.track_id,
                direction="entry" if direction == 1 else "exit",
                centroid=curr,
            )
        return TriggerResult.no()
