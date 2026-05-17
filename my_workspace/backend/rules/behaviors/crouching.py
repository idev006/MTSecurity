"""Crouching behavior — triggers when object height drops significantly below its baseline."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from rules.behaviors.base import RuleBehavior, TriggerResult

if TYPE_CHECKING:
    from ai.tracker import Track
    from rules.dwell_tracker import DwellTracker
    from rules.zone_manager import ZoneManager


class CrouchingBehavior(RuleBehavior):
    name = "crouching"

    def __init__(self) -> None:
        self._baseline_heights: dict[tuple[int, int], float] = {}
        self._sample_counts: dict[tuple[int, int], int] = {}
        self._crouch_frames: dict[tuple[int, int], int] = {}

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
        height_ratio_threshold = params.get("height_ratio_threshold", 0.6)
        min_frames = params.get("min_frames", 3)
        baseline_frames = params.get("baseline_frames", 15)

        bbox = track.bbox
        h = bbox["y2"] - bbox["y1"]
        if h <= 0:
            return TriggerResult.no()

        key = (rule_id, track.track_id)
        count = self._sample_counts.get(key, 0)

        if count < baseline_frames:
            # Build running average baseline
            prev_avg = self._baseline_heights.get(key, h)
            self._baseline_heights[key] = (prev_avg * count + h) / (count + 1)
            self._sample_counts[key] = count + 1
            return TriggerResult.no()

        baseline = self._baseline_heights[key]
        if baseline <= 0:
            return TriggerResult.no()

        ratio = h / baseline
        if ratio < height_ratio_threshold:
            self._crouch_frames[key] = self._crouch_frames.get(key, 0) + 1
            if self._crouch_frames[key] >= min_frames:
                confidence = min(1.0, (1.0 - ratio) / (1.0 - height_ratio_threshold))
                return TriggerResult.yes(
                    confidence=confidence,
                    track_id=track.track_id,
                    height_ratio=round(ratio, 3),
                    centroid=track.centroid,
                    bbox=bbox,
                )
        else:
            self._crouch_frames[key] = 0

        return TriggerResult.no()
