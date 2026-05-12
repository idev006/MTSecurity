"""InferenceEngine — OpenVINO 2026.x compiled model wrapper."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np

from ai.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


class InferenceEngine:
    """
    Wraps a single OpenVINO compiled model for synchronous inference.

    Input preprocessing:
      - Resize to model input shape (e.g. 640×640 for YOLOv11n)
      - Normalize to [0,1] float32
      - HWC → NCHW

    Returns raw model output tensor(s) + inference time in ms.
    """

    def __init__(self, registry: ModelRegistry, model_name: str, model_path: Path) -> None:
        self._compiled = registry.load(model_name, model_path)
        self._infer_req = self._compiled.create_infer_request() if self._compiled else None
        self._input_shape: tuple[int, int] = (640, 640)   # default YOLOv11n

        if self._compiled is not None:
            shape = self._compiled.input(0).shape
            # shape: [1, 3, H, W]
            self._input_shape = (int(shape[2]), int(shape[3]))
            logger.info("InferenceEngine ready — input %s on %s", self._input_shape, registry._device)
        else:
            logger.warning("InferenceEngine: no compiled model — running in dummy mode")

    def infer(self, frame_rgb: np.ndarray) -> tuple[list[np.ndarray], float]:
        """
        Run inference on a single RGB frame.

        Returns:
            outputs  — list of output tensors (raw)
            elapsed  — inference time in milliseconds
        """
        if self._infer_req is None:
            # Dummy mode: return empty output
            return [], 0.0

        blob = self._preprocess(frame_rgb)
        t0 = time.perf_counter()
        self._infer_req.infer({0: blob})
        elapsed_ms = (time.perf_counter() - t0) * 1000

        outputs = [
            self._infer_req.get_output_tensor(i).data.copy()
            for i in range(len(self._compiled.outputs))
        ]
        return outputs, elapsed_ms

    # ── Internal ──────────────────────────────────────────────────────────────

    def _preprocess(self, frame_rgb: np.ndarray) -> np.ndarray:
        import cv2
        h, w = self._input_shape
        resized = cv2.resize(frame_rgb, (w, h), interpolation=cv2.INTER_LINEAR)
        blob = resized.astype(np.float32) / 255.0   # normalize [0,1]
        blob = np.transpose(blob, (2, 0, 1))         # HWC → CHW
        blob = np.expand_dims(blob, axis=0)          # add batch dim → NCHW
        return blob

    @property
    def is_ready(self) -> bool:
        return self._infer_req is not None
