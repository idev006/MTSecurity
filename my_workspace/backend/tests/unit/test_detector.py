"""Phase 2 Gate — Detector: NMS, postprocess, boundary conditions."""

from __future__ import annotations

import numpy as np
import pytest

from ai.detector import Detection, _compute_iou, _nms, postprocess_yolo


# ── IoU ───────────────────────────────────────────────────────────────────────

def test_iou_identical_boxes():
    box = np.array([0.1, 0.1, 0.5, 0.5])
    others = np.array([[0.1, 0.1, 0.5, 0.5]])
    iou = _compute_iou(box, others)
    assert abs(iou[0] - 1.0) < 1e-6


def test_iou_no_overlap():
    box = np.array([0.0, 0.0, 0.2, 0.2])
    others = np.array([[0.5, 0.5, 0.9, 0.9]])
    iou = _compute_iou(box, others)
    assert iou[0] == 0.0


def test_iou_partial_overlap():
    box = np.array([0.0, 0.0, 0.5, 0.5])
    others = np.array([[0.25, 0.25, 0.75, 0.75]])
    iou = _compute_iou(box, others)
    assert 0.0 < iou[0] < 1.0


# ── NMS ───────────────────────────────────────────────────────────────────────

def test_nms_removes_overlapping_lower_score():
    boxes = np.array([[0.0, 0.0, 0.5, 0.5], [0.05, 0.05, 0.55, 0.55]])
    scores = np.array([0.9, 0.7])
    keep = _nms(boxes, scores, iou_threshold=0.45)
    assert keep == [0]   # higher score survives


def test_nms_keeps_non_overlapping():
    boxes = np.array([[0.0, 0.0, 0.2, 0.2], [0.5, 0.5, 0.9, 0.9]])
    scores = np.array([0.9, 0.8])
    keep = _nms(boxes, scores, iou_threshold=0.45)
    assert set(keep) == {0, 1}


def test_nms_single_box():
    boxes = np.array([[0.1, 0.1, 0.5, 0.5]])
    scores = np.array([0.95])
    keep = _nms(boxes, scores, iou_threshold=0.45)
    assert keep == [0]


# ── Detection dataclass ───────────────────────────────────────────────────────

def test_detection_centroid():
    d = Detection(label="person", class_id=0, confidence=0.9,
                  x1=0.2, y1=0.3, x2=0.6, y2=0.7)
    cx, cy = d.centroid
    assert abs(cx - 0.4) < 1e-6
    assert abs(cy - 0.5) < 1e-6


def test_detection_area():
    d = Detection(label="person", class_id=0, confidence=0.9,
                  x1=0.0, y1=0.0, x2=0.5, y2=0.4)
    assert abs(d.area - 0.2) < 1e-6


# ── postprocess_yolo ──────────────────────────────────────────────────────────

def _make_yolo_output(
    num_anchors: int = 8400,
    num_classes: int = 80,
    inject_person: bool = False,
) -> list[np.ndarray]:
    """Create a synthetic YOLO output tensor [1, 84, 8400]."""
    raw = np.zeros((1, num_classes + 4, num_anchors), dtype=np.float32)
    if inject_person:
        # Put a high-confidence person box at anchor 100
        raw[0, 0, 100] = 320.0   # cx (input space, 640×640)
        raw[0, 1, 100] = 320.0   # cy
        raw[0, 2, 100] = 100.0   # w
        raw[0, 3, 100] = 200.0   # h
        raw[0, 4, 100] = 0.95    # person confidence (class 0)
    return [raw]


def test_postprocess_empty_output_returns_empty():
    result = postprocess_yolo([], orig_w=1920, orig_h=1080)
    assert result == []


def test_postprocess_no_detections_above_threshold():
    output = _make_yolo_output(inject_person=False)
    result = postprocess_yolo(output, orig_w=1920, orig_h=1080, confidence_threshold=0.6)
    assert result == []


def test_postprocess_detects_injected_person():
    output = _make_yolo_output(inject_person=True)
    result = postprocess_yolo(output, orig_w=1920, orig_h=1080, confidence_threshold=0.6)
    assert len(result) >= 1
    person = next((d for d in result if d.label == "person"), None)
    assert person is not None
    assert person.confidence >= 0.6


def test_postprocess_normalised_coords_in_range():
    output = _make_yolo_output(inject_person=True)
    result = postprocess_yolo(output, orig_w=1920, orig_h=1080, confidence_threshold=0.5)
    for det in result:
        assert 0.0 <= det.x1 <= 1.0
        assert 0.0 <= det.y1 <= 1.0
        assert 0.0 <= det.x2 <= 1.0
        assert 0.0 <= det.y2 <= 1.0
        assert det.x1 < det.x2
        assert det.y1 < det.y2


def test_postprocess_class_filter():
    output = _make_yolo_output(inject_person=True)
    # Only allow car (class 2) — should find nothing
    result = postprocess_yolo(
        output, orig_w=1920, orig_h=1080,
        confidence_threshold=0.5, target_classes=[2]
    )
    assert not any(d.label == "person" for d in result)
