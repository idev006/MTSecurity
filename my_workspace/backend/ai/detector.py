"""Detector — YOLOv8/v11 output postprocessing → Detection objects."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# COCO class labels (indices 0-79); we care most about person=0
COCO_LABELS = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
    "truck", "boat", "traffic light", "fire hydrant", "stop sign",
    "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
    "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
    "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
    "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
    "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
    "couch", "potted plant", "bed", "dining table", "toilet", "tv",
    "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
    "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
]


@dataclass
class Detection:
    label: str
    class_id: int
    confidence: float
    x1: float   # normalised 0.0–1.0
    y1: float
    x2: float
    y2: float

    @property
    def centroid(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)


def postprocess_yolo(
    outputs: list[np.ndarray],
    orig_w: int,
    orig_h: int,
    input_size: int = 640,
    confidence_threshold: float = 0.6,
    iou_threshold: float = 0.45,
    target_classes: list[int] | None = None,
) -> list[Detection]:
    """
    Parse YOLOv8/v11 output tensor → list of Detection.

    YOLOv8/v11 output shape: [1, num_classes+4, num_anchors]
    Layout per anchor: [cx, cy, w, h, cls0_conf, cls1_conf, ...]
    Coordinates are in input-space (0–640).
    """
    if not outputs:
        return []

    raw = outputs[0]  # shape [1, 84, 8400] for COCO 80-class
    if raw.ndim == 3:
        raw = raw[0]   # → [84, 8400]

    # Transpose to [8400, 84] — each row is one anchor
    raw = raw.T        # → [8400, 84]

    boxes_xywh = raw[:, :4]
    class_scores = raw[:, 4:]

    class_ids = np.argmax(class_scores, axis=1)
    confidences = class_scores[np.arange(len(class_ids)), class_ids]

    # Filter by confidence
    mask = confidences >= confidence_threshold
    if target_classes is not None:
        mask &= np.isin(class_ids, target_classes)

    boxes_xywh = boxes_xywh[mask]
    confidences = confidences[mask]
    class_ids = class_ids[mask]

    if len(boxes_xywh) == 0:
        return []

    # Convert cx,cy,w,h (input-space) → x1,y1,x2,y2 (normalised)
    scale_x = 1.0 / input_size
    scale_y = 1.0 / input_size

    cx = boxes_xywh[:, 0] * scale_x
    cy = boxes_xywh[:, 1] * scale_y
    bw = boxes_xywh[:, 2] * scale_x
    bh = boxes_xywh[:, 3] * scale_y

    x1 = np.clip(cx - bw / 2, 0, 1)
    y1 = np.clip(cy - bh / 2, 0, 1)
    x2 = np.clip(cx + bw / 2, 0, 1)
    y2 = np.clip(cy + bh / 2, 0, 1)

    # NMS
    boxes_xyxy = np.stack([x1, y1, x2, y2], axis=1).astype(np.float32)
    keep = _nms(boxes_xyxy, confidences, iou_threshold)

    detections: list[Detection] = []
    for i in keep:
        cid = int(class_ids[i])
        label = COCO_LABELS[cid] if cid < len(COCO_LABELS) else f"class_{cid}"
        detections.append(Detection(
            label=label,
            class_id=cid,
            confidence=float(confidences[i]),
            x1=float(x1[i]),
            y1=float(y1[i]),
            x2=float(x2[i]),
            y2=float(y2[i]),
        ))
    return detections


def _nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float) -> list[int]:
    """Vectorised Non-Maximum Suppression."""
    order = scores.argsort()[::-1]
    keep: list[int] = []

    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break

        rest = order[1:]
        iou = _compute_iou(boxes[i], boxes[rest])
        order = rest[iou <= iou_threshold]

    return keep


def _compute_iou(box: np.ndarray, others: np.ndarray) -> np.ndarray:
    inter_x1 = np.maximum(box[0], others[:, 0])
    inter_y1 = np.maximum(box[1], others[:, 1])
    inter_x2 = np.minimum(box[2], others[:, 2])
    inter_y2 = np.minimum(box[3], others[:, 3])

    inter_w = np.clip(inter_x2 - inter_x1, 0, None)
    inter_h = np.clip(inter_y2 - inter_y1, 0, None)
    inter_area = inter_w * inter_h

    area_a = (box[2] - box[0]) * (box[3] - box[1])
    area_b = (others[:, 2] - others[:, 0]) * (others[:, 3] - others[:, 1])
    union = area_a + area_b - inter_area

    return np.where(union > 0, inter_area / union, 0.0)
