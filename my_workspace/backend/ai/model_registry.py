"""ModelRegistry — load and cache OpenVINO IR models."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import openvino as ov
    _OV_AVAILABLE = True
except ImportError:
    _OV_AVAILABLE = False
    logger.warning("OpenVINO not available — AI inference disabled")


class ModelRegistry:
    """
    Loads OpenVINO IR models (.xml + .bin) and caches compiled instances.

    Usage:
        registry = ModelRegistry(device="CPU")
        compiled = registry.get("yolov11n")
    """

    def __init__(self, device: str = "CPU") -> None:
        self._device = device
        self._cache: dict[str, "ov.CompiledModel"] = {}
        self._core: "ov.Core | None" = ov.Core() if _OV_AVAILABLE else None

    def load(self, name: str, model_path: Path) -> "ov.CompiledModel | None":
        """Load and compile a model from disk. Returns None if OpenVINO unavailable."""
        if not _OV_AVAILABLE or self._core is None:
            return None

        if name in self._cache:
            return self._cache[name]

        xml_path = model_path if model_path.suffix == ".xml" else model_path.with_suffix(".xml")
        if not xml_path.exists():
            logger.error("Model file not found: %s", xml_path)
            return None

        logger.info("Loading model '%s' from %s on %s", name, xml_path, self._device)
        model = self._core.read_model(str(xml_path))
        compiled = self._core.compile_model(model, self._device)
        self._cache[name] = compiled
        logger.info("Model '%s' loaded — input shape: %s", name, compiled.input(0).shape)
        return compiled

    def get(self, name: str) -> "ov.CompiledModel | None":
        return self._cache.get(name)

    def available_devices(self) -> list[str]:
        if self._core is None:
            return []
        return self._core.available_devices

    @property
    def is_available(self) -> bool:
        return _OV_AVAILABLE
