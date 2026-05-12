"""Phase 2 Gate — FrameCodec: encode/decode, resize tiers."""

from __future__ import annotations

import numpy as np
import pytest

from ingestion.frame_codec import (
    ResolutionTier,
    decode_frame,
    encode_frame,
    frame_to_rgb,
    get_frame_dims,
    resize_for_inference,
)


def _blank_frame(w: int = 640, h: int = 480, color=(128, 64, 32)) -> np.ndarray:
    """BGR ndarray filled with a single color."""
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    frame[:] = color
    return frame


# ── encode / decode round-trip ────────────────────────────────────────────────

def test_encode_returns_bytes():
    frame = _blank_frame()
    data = encode_frame(frame, ResolutionTier.THUMBNAIL)
    assert isinstance(data, bytes)
    assert len(data) > 0


def test_encode_decode_roundtrip_preserves_shape():
    frame = _blank_frame(640, 480)
    data = encode_frame(frame, ResolutionTier.THUMBNAIL)
    decoded = decode_frame(data)
    # Thumbnail is 320×180
    assert decoded.shape == (180, 320, 3)


def test_decode_invalid_bytes_raises():
    with pytest.raises(ValueError, match="JPEG decode"):
        decode_frame(b"not a jpeg")


# ── Resolution tiers ──────────────────────────────────────────────────────────

def test_thumbnail_dimensions():
    w, h = get_frame_dims(ResolutionTier.THUMBNAIL)
    assert w == 320 and h == 180


def test_monitor_dimensions():
    w, h = get_frame_dims(ResolutionTier.MONITOR)
    assert w == 640 and h == 360


def test_detail_dimensions():
    w, h = get_frame_dims(ResolutionTier.DETAIL)
    assert w == 1280 and h == 720


def test_encode_thumbnail_produces_smaller_file_than_detail():
    frame = _blank_frame(1280, 720)
    thumb = encode_frame(frame, ResolutionTier.THUMBNAIL)
    detail = encode_frame(frame, ResolutionTier.DETAIL)
    assert len(thumb) < len(detail)


# ── frame_to_rgb ──────────────────────────────────────────────────────────────

def test_frame_to_rgb_swaps_channels():
    bgr = np.zeros((10, 10, 3), dtype=np.uint8)
    bgr[:, :, 0] = 255   # Blue channel
    rgb = frame_to_rgb(bgr)
    assert rgb[0, 0, 2] == 255   # Red channel in RGB
    assert rgb[0, 0, 0] == 0


# ── resize_for_inference ──────────────────────────────────────────────────────

def test_resize_for_inference_output_shape():
    frame = _blank_frame(1920, 1080)
    canvas, scale, pad_top, pad_left = resize_for_inference(frame, target_size=640)
    assert canvas.shape == (640, 640, 3)


def test_resize_for_inference_scale_correct():
    frame = _blank_frame(1280, 720)
    _, scale, _, _ = resize_for_inference(frame, target_size=640)
    # Max dimension is 1280, so scale = 640/1280 = 0.5
    assert abs(scale - 0.5) < 1e-6


def test_resize_square_frame_no_padding():
    frame = _blank_frame(640, 640)
    canvas, scale, pad_top, pad_left = resize_for_inference(frame, target_size=640)
    assert pad_top == 0
    assert pad_left == 0
    assert abs(scale - 1.0) < 1e-6
