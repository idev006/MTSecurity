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
    - publish_nowait() is thread-safe via call_soon_threadsafe
    """

    def __init__(self, maxsize: int = 1000) -> None:
        self._queue: asyncio.PriorityQueue[tuple[int, MTPMessage]] = asyncio.PriorityQueue(
            maxsize=maxsize
        )
        self._subscribers: dict[str, list[Handler]] = defaultdict(list)
        self._task: asyncio.Task | None = None
        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None

    async def start(self) -> None:
        self._running = True
        self._loop = asyncio.get_running_loop()
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
        """Thread-safe non-blocking publish — drops silently if queue full or bus not started."""
        if self._loop is None:
            return
        try:
            self._loop.call_soon_threadsafe(self._put_nowait, message)
        except RuntimeError:
            # loop is closed (shutting down)
            pass

    def _put_nowait(self, message: MTPMessage) -> None:
        """Must only be called from the event loop thread."""
        try:
            self._queue.put_nowait((message.priority.value, message))
        except asyncio.QueueFull:
            logger.debug("MessageBus queue full — dropped %s", message.msg_type)

    async def _dispatch_loop(self) -> None:
        # Deliberately avoid asyncio.wait_for(queue.get(), timeout=…) — on Python
        # < 3.12 a timed-out get() leaves a cancelled waiter in the queue which
        # causes InvalidStateError on the next put_nowait, silently killing this
        # task.  Instead we rely on task.cancel() (called by stop()) to break out.
        while self._running:
            try:
                _, message = await self._queue.get()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("MessageBus: unexpected error in queue.get()")
                continue

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
