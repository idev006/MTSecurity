"""MessageBus — asyncio priority queue with typed subscriptions."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable

from protocol.mtp import MTPMessage, MTPPriority

logger = logging.getLogger(__name__)

Handler = Callable[[MTPMessage], Awaitable[None]]


class MessageBus:
    """
    In-process async priority message bus.

    - Priority queue: CRITICAL(1) > HIGH(2) > NORMAL(3) > LOW(4)
    - Expired messages (TTL exceeded) are silently dropped
    - Exceptions in handlers are logged, not propagated
    """

    def __init__(self, maxsize: int = 1000) -> None:
        self._queue: asyncio.PriorityQueue[tuple[int, MTPMessage]] = asyncio.PriorityQueue(
            maxsize=maxsize
        )
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._dispatch_loop(), name="message-bus")
        logger.info("MessageBus started")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("MessageBus stopped")

    def subscribe(self, msg_type: str, handler: Handler) -> None:
        """Register an async handler for a message type."""
        self._subscribers[msg_type].append(handler)

    def unsubscribe(self, msg_type: str, handler: Handler) -> None:
        self._subscribers[msg_type] = [
            h for h in self._subscribers[msg_type] if h is not handler
        ]

    async def publish(self, message: MTPMessage) -> None:
        """Enqueue a message. Blocks if queue is full (back-pressure)."""
        await self._queue.put((message.priority.value, message))

    def publish_nowait(self, message: MTPMessage) -> None:
        """Non-blocking publish — raises QueueFull if at capacity."""
        self._queue.put_nowait((message.priority.value, message))

    async def _dispatch_loop(self) -> None:
        while self._running:
            try:
                _, message = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            if message.is_expired():
                logger.debug("Dropped expired message: %s id=%s", message.msg_type, message.message_id)
                self._queue.task_done()
                continue

            handlers = self._subscribers.get(message.msg_type, [])
            if handlers:
                await asyncio.gather(
                    *[self._safe_call(h, message) for h in handlers],
                    return_exceptions=True,
                )
            self._queue.task_done()

    @staticmethod
    async def _safe_call(handler: Handler, message: MTPMessage) -> None:
        try:
            await handler(message)
        except Exception:
            logger.exception(
                "Handler %s failed for message type %s",
                getattr(handler, "__qualname__", repr(handler)),
                message.msg_type,
            )

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    async def wait_empty(self) -> None:
        """Wait until the queue is fully processed (useful in tests)."""
        await self._queue.join()
