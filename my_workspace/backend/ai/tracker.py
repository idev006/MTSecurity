"""IoU-based multi-object tracker with stable track IDs."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ai.detector import Detection


@dataclass
class Track:
    track_id: int
    label: str
    class_id: int
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    age: int = 0           # frames since last match
    hits: int = 1          # total frames matched

    @property
    def centroid(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return self.x1, self.y1, self.x2, self.y2

    def update(self, det: Detection) -> None:
        self.x1, self.y1, self.x2, self.y2 = det.x1, det.y1, det.x2, det.y2
        self.confidence = det.confidence
        self.age = 0
        self.hits += 1


_IOU_THRESHOLD = 0.35   # minimum overlap to match detection to track
_MAX_AGE = 20           # frames a track survives without a match
                        # 20 frames ≈ 2s at 10 fps — gives stationary objects time
                        # to survive brief detection gaps (flickering confidence)


class ObjectTracker:
    """
    Greedy IoU-based tracker (simplified ByteTrack-style).

    Each frame:
      1. Match existing tracks to new detections by IoU
      2. Update matched tracks
      3. Create new tracks for unmatched detections
      4. Age out tracks missing for > MAX_AGE frames
    """

    def __init__(self, iou_threshold: float = _IOU_THRESHOLD, max_age: int = _MAX_AGE) -> None:
        self._iou_thresh = iou_threshold
        self._max_age = max_age
        self._tracks: list[Track] = []
        self._next_id = 1

    def update(self, detections: list[Detection]) -> list[Track]:
        """Returns list of active tracks after matching with new detections."""
        if not detections:
            for t in self._tracks:
                t.age += 1
            self._tracks = [t for t in self._tracks if t.age <= self._max_age]
            return list(self._tracks)

        if not self._tracks:
            for det in detections:
                self._tracks.append(self._new_track(det))
            return list(self._tracks)

        # Build IoU matrix [tracks × detections]
        track_boxes = np.array([list(t.bbox) for t in self._tracks])
        det_boxes   = np.array([[d.x1, d.y1, d.x2, d.y2] for d in detections])
        iou_matrix  = _iou_matrix(track_boxes, det_boxes)

        matched_tracks: set[int] = set()
        matched_dets: set[int]   = set()

        # Greedy matching: highest IoU first
        flat_order = np.argsort(-iou_matrix, axis=None)
        for idx in flat_order:
            ti, di = divmod(int(idx), len(detections))
            if ti in matched_tracks or di in matched_dets:
                continue
            if iou_matrix[ti, di] >= self._iou_thresh:
                self._tracks[ti].update(detections[di])
                matched_tracks.add(ti)
                matched_dets.add(di)

        # Age unmatched tracks
        for ti, track in enumerate(self._tracks):
            if ti not in matched_tracks:
                track.age += 1

        # Spawn new tracks for unmatched detections
        for di, det in enumerate(detections):
            if di not in matched_dets:
                self._tracks.append(self._new_track(det))

        # Remove stale tracks
        self._tracks = [t for t in self._tracks if t.age <= self._max_age]
        return list(self._tracks)

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1

    def _new_track(self, det: Detection) -> Track:
        t = Track(
            track_id=self._next_id,
            label=det.label,
            class_id=det.class_id,
            x1=det.x1, y1=det.y1, x2=det.x2, y2=det.y2,
            confidence=det.confidence,
        )
        self._next_id += 1
        return t


def _iou_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute IoU between every pair of boxes in a (N,4) and b (M,4)."""
    inter_x1 = np.maximum(a[:, 0:1], b[:, 0])
    inter_y1 = np.maximum(a[:, 1:2], b[:, 1])
    inter_x2 = np.minimum(a[:, 2:3], b[:, 2])
    inter_y2 = np.minimum(a[:, 3:4], b[:, 3])

    iw = np.clip(inter_x2 - inter_x1, 0, None)
    ih = np.clip(inter_y2 - inter_y1, 0, None)
    inter = iw * ih

    area_a = (a[:, 2] - a[:, 0]) * (a[:, 3] - a[:, 1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    union  = area_a[:, None] + area_b[None, :] - inter

    return np.where(union > 0, inter / union, 0.0)
