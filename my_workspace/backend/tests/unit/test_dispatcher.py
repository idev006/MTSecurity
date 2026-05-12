"""Unit tests for NotificationDispatcher."""

from __future__ import annotations

import asyncio

import pytest

from alerts.notifications.base import AlertPayload, NotificationChannel, SendResult
from alerts.notifications.dispatcher import NotificationDispatcher


def _payload() -> AlertPayload:
    return AlertPayload(
        event_id=1,
        rule_name="test_rule",
        camera_id=1,
        camera_name="Cam 1",
        behavior="intrusion",
        severity="high",
        confidence=0.9,
        snapshot_url=None,
        clip_url=None,
        occurred_at="2026-01-01T00:00:00+00:00",
    )


class _OkChannel(NotificationChannel):
    channel_name = "ok_channel"

    async def send(self, payload: AlertPayload) -> SendResult:
        return self._result(True)


class _FailChannel(NotificationChannel):
    channel_name = "fail_channel"

    async def send(self, payload: AlertPayload) -> SendResult:
        return self._result(False, "simulated failure")


class _ExceptionChannel(NotificationChannel):
    channel_name = "exc_channel"

    async def send(self, payload: AlertPayload) -> SendResult:
        raise RuntimeError("boom")


class TestNotificationDispatcher:
    def test_empty_dispatcher_returns_empty(self):
        d = NotificationDispatcher()
        results = asyncio.run(d.dispatch(_payload()))
        assert results == []

    def test_single_ok_channel_succeeds(self):
        d = NotificationDispatcher()
        d.add_channel(_OkChannel())
        results = asyncio.run(d.dispatch(_payload()))
        assert len(results) == 1
        assert results[0].success is True
        assert results[0].channel == "ok_channel"

    def test_single_fail_channel_returns_failure(self):
        d = NotificationDispatcher()
        d.add_channel(_FailChannel())
        results = asyncio.run(d.dispatch(_payload()))
        assert results[0].success is False

    def test_exception_channel_does_not_crash_dispatcher(self):
        d = NotificationDispatcher()
        d.add_channel(_ExceptionChannel())
        results = asyncio.run(d.dispatch(_payload()))
        assert len(results) == 1
        assert results[0].success is False
        assert "boom" in (results[0].error or "")

    def test_failure_does_not_stop_other_channels(self):
        d = NotificationDispatcher()
        d.add_channel(_FailChannel())
        d.add_channel(_OkChannel())
        d.add_channel(_ExceptionChannel())
        results = asyncio.run(d.dispatch(_payload()))
        assert len(results) == 3
        successes = [r for r in results if r.success]
        assert len(successes) == 1
        assert successes[0].channel == "ok_channel"

    def test_remove_channel(self):
        d = NotificationDispatcher()
        d.add_channel(_OkChannel())
        d.add_channel(_FailChannel())
        d.remove_channel("fail_channel")
        assert d.channel_count == 1
        results = asyncio.run(d.dispatch(_payload()))
        assert all(r.success for r in results)

    def test_channel_count(self):
        d = NotificationDispatcher()
        assert d.channel_count == 0
        d.add_channel(_OkChannel())
        assert d.channel_count == 1
        d.add_channel(_FailChannel())
        assert d.channel_count == 2

    def test_concurrent_dispatch_all_called(self):
        called = []

        class _RecordChannel(NotificationChannel):
            channel_name = "rec"

            async def send(self, payload: AlertPayload) -> SendResult:
                called.append(1)
                return self._result(True)

        d = NotificationDispatcher()
        for _ in range(5):
            d.add_channel(_RecordChannel())
        asyncio.run(d.dispatch(_payload()))
        assert len(called) == 5
