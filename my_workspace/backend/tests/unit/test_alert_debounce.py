"""Unit tests for AlertManager notification debounce (FEAT-016)."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alerts.alert_manager import AlertManager, _NOTIF_DEBOUNCE_SECONDS


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_manager(debounce: float = _NOTIF_DEBOUNCE_SECONDS) -> AlertManager:
    """Build an AlertManager with all heavy deps mocked out."""
    mgr = AlertManager.__new__(AlertManager)
    # Wire only the attributes accessed by _dispatch_notifications
    mgr._dispatcher = AsyncMock()
    mgr._dispatcher.dispatch = AsyncMock(return_value=[
        MagicMock(channel="line", success=True),
    ])
    mgr._notif_last_fired = {}
    return mgr


def _make_alert(camera_id: int = 1):
    from alerts.notifications.base import AlertPayload
    return AlertPayload(
        event_id=1,
        rule_name="TestRule",
        camera_id=camera_id,
        camera_name="Cam1",
        behavior="intrusion",
        severity="high",
        confidence=0.92,
        snapshot_url=None,
        clip_url=None,
        occurred_at="2026-01-01T00:00:00Z",
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestNotificationDebounce:
    async def test_first_notification_always_sent(self):
        mgr = _make_manager()
        await mgr._dispatch_notifications(_make_alert(camera_id=1), event_id=1)
        mgr._dispatcher.dispatch.assert_awaited_once()

    async def test_second_notification_suppressed_within_debounce(self):
        mgr = _make_manager()
        await mgr._dispatch_notifications(_make_alert(camera_id=1), event_id=1)
        await mgr._dispatch_notifications(_make_alert(camera_id=1), event_id=2)
        # Still only 1 dispatch call — second was suppressed
        assert mgr._dispatcher.dispatch.await_count == 1

    async def test_different_cameras_are_independent(self):
        """Camera 1 debounce must not affect Camera 2."""
        mgr = _make_manager()
        await mgr._dispatch_notifications(_make_alert(camera_id=1), event_id=1)
        await mgr._dispatch_notifications(_make_alert(camera_id=2), event_id=2)
        # Both cameras fire independently
        assert mgr._dispatcher.dispatch.await_count == 2

    async def test_notification_allowed_after_debounce_expires(self):
        mgr = _make_manager()
        # Manually set last_fired to a time far in the past
        mgr._notif_last_fired[1] = time.monotonic() - (_NOTIF_DEBOUNCE_SECONDS + 1)
        await mgr._dispatch_notifications(_make_alert(camera_id=1), event_id=99)
        mgr._dispatcher.dispatch.assert_awaited_once()

    async def test_debounce_timestamp_updated_on_success(self):
        mgr = _make_manager()
        before = time.monotonic()
        await mgr._dispatch_notifications(_make_alert(camera_id=1), event_id=1)
        after = time.monotonic()

        ts = mgr._notif_last_fired.get(1)
        assert ts is not None
        assert before <= ts <= after

    async def test_debounce_not_updated_when_dispatch_fails(self):
        """If dispatch raises, the timestamp must not advance (allow retry)."""
        mgr = _make_manager()
        mgr._dispatcher.dispatch.side_effect = RuntimeError("network error")

        await mgr._dispatch_notifications(_make_alert(camera_id=1), event_id=1)
        assert 1 not in mgr._notif_last_fired

    async def test_suppressed_event_does_not_reset_timer(self):
        """Suppressed notifications must not update the debounce timestamp."""
        mgr = _make_manager()
        await mgr._dispatch_notifications(_make_alert(camera_id=1), event_id=1)
        first_ts = mgr._notif_last_fired[1]

        await mgr._dispatch_notifications(_make_alert(camera_id=1), event_id=2)
        assert mgr._notif_last_fired[1] == first_ts   # unchanged
