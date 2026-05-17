"""Running behavior — triggers when object moves faster than a speed threshold."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

from rules.behaviors.base import RuleBehavior, TriggerResult

if TYPE_CHECKING:
    from ai.tracker import Track
    from rules.dwell_tracker import DwellTracker
    from rules.zone_manager import ZoneManager


class RunningBehavior(RuleBehavior):
    name = "running"

    def __init__(self) -> None:
        self._prev_centroids: dict[tuple[int, int], tuple[float, float]] = {}
        self._fast_frames: dict[tuple[int, int], int] = {}

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
            return TriggerResult.no()

        params = config.get("behavior_params") or {}
        speed_threshold = params.get("speed_threshold", 0.04)
        min_frames = params.get("min_frames", 3)

        key = (rule_id, track.track_id)
        curr = track.centroid

        if key not in self._prev_centroids:
            self._prev_centroids[key] = curr
            self._fast_frames[key] = 0
            return TriggerResult.no()

        prev = self._prev_centroids[key]
        self._prev_centroids[key] = curr

        velocity = math.sqrt((curr[0] - prev[0]) ** 2 + (curr[1] - prev[1]) ** 2)

        if velocity > speed_threshold:
            self._fast_frames[key] = self._fast_frames.get(key, 0) + 1
            if self._fast_frames[key] >= min_frames:
                confidence = min(1.0, velocity / speed_threshold)
                return TriggerResult.yes(
                    confidence=confidence,
                    track_id=track.track_id,
                    velocity=round(velocity, 4),
                    centroid=curr,
                    bbox=track.bbox,
                )
        else:
            self._fast_frames[key] = 0

        return TriggerResult.no()
