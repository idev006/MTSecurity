"""Phase 2 Gate — FrameBuffer thread-safety and correctness."""

from __future__ import annotations

import threading
from datetime import datetime, timezone

from ingestion.frame_buffer import Frame, FrameBuffer


def _make_frame(camera_id: int, data: bytes = b"jpeg") -> Frame:
    return Frame(
        camera_id=camera_id,
        data=data,
        width=320, height=180,
        captured_at=datetime.now(timezone.utc),
    )


def test_put_and_get_single_camera():
    buf = FrameBuffer()
    f = _make_frame(1, b"frame1")
    buf.put(f)
    result = buf.get(1)
    assert result is not None
    assert result.data == b"frame1"


def test_get_returns_none_for_unknown_camera():
    buf = FrameBuffer()
    assert buf.get(99) is None


def test_put_overwrites_old_frame():
    buf = FrameBuffer()
    buf.put(_make_frame(1, b"old"))
    buf.put(_make_frame(1, b"new"))
    assert buf.get(1).data == b"new"


def test_multiple_cameras_independent():
    buf = FrameBuffer()
    buf.put(_make_frame(1, b"cam1"))
    buf.put(_make_frame(2, b"cam2"))
    assert buf.get(1).data == b"cam1"
    assert buf.get(2).data == b"cam2"


def test_get_all_latest():
    buf = FrameBuffer()
    buf.put(_make_frame(1, b"a"))
    buf.put(_make_frame(2, b"b"))
    buf.put(_make_frame(3, b"c"))
    latest = buf.get_all_latest()
    assert set(latest.keys()) == {1, 2, 3}


def test_remove_camera():
    buf = FrameBuffer()
    buf.put(_make_frame(1, b"data"))
    buf.remove(1)
    assert buf.get(1) is None


def test_active_camera_ids():
    buf = FrameBuffer()
    buf.put(_make_frame(5, b"x"))
    buf.put(_make_frame(7, b"y"))
    ids = buf.active_camera_ids()
    assert 5 in ids and 7 in ids


def test_thread_safety_concurrent_writes():
    """Multiple threads writing different cameras concurrently — no crash, no data mix."""
    buf = FrameBuffer()
    errors: list[Exception] = []

    def writer(camera_id: int):
        try:
            for _ in range(100):
                buf.put(_make_frame(camera_id, f"cam{camera_id}".encode()))
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    # Each camera slot must hold its own data
    for i in range(10):
        frame = buf.get(i)
        assert frame is not None
        assert frame.data == f"cam{i}".encode()
