"""Fall detection behavior — triggers when bounding box aspect ratio indicates a fallen person."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rules.behaviors.base import RuleBehavior, TriggerResult

if TYPE_CHECKING:
    from ai.tracker import Track
    from rules.dwell_tracker import DwellTracker
    from rules.zone_manager import ZoneManager


class FallDetectionBehavior(RuleBehavior):
    name = "fall_detection"

    def __init__(self) -> None:
        self._fall_frames: dict[tuple[int, int], int] = {}

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
        aspect_ratio_threshold = params.get("aspect_ratio_threshold", 1.5)
        min_frames = params.get("min_frames", 2)

        bbox = track.bbox
        w = bbox["x2"] - bbox["x1"]
        h = bbox["y2"] - bbox["y1"]
        if h <= 0:
            return TriggerResult.no()

        aspect_ratio = w / h
        key = (rule_id, track.track_id)

        if aspect_ratio > aspect_ratio_threshold:
            self._fall_frames[key] = self._fall_frames.get(key, 0) + 1
            if self._fall_frames[key] >= min_frames:
                confidence = min(1.0, aspect_ratio / aspect_ratio_threshold)
                return TriggerResult.yes(
                    confidence=confidence,
                    track_id=track.track_id,
                    aspect_ratio=round(aspect_ratio, 3),
                    centroid=track.centroid,
                    bbox=bbox,
                )
        else:
            self._fall_frames[key] = 0

        return TriggerResult.no()
