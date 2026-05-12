"""ConfigService — DB-backed SSOT for all mutable configuration."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from cachetools import TTLCache
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from models.camera import Camera
from models.rule import Rule
from models.zone import Zone
from protocol.message_bus import MessageBus
from protocol.mtp import MTPMessage, MTPMsgType, MTPPriority
from protocol.payloads import ConfigChangedPayload

logger = logging.getLogger(__name__)

_CACHE_TTL = 60     # seconds
_CACHE_MAX = 1024   # items


class ConfigService:
    """
    Single Source of Truth for persisted configuration.

    - Reads from DB, caches with 60s TTL (cachetools.TTLCache — no Redis)
    - Every mutation publishes CONFIG_CHANGED on the bus
    - Consumers (RuleEngine, CameraManager) subscribe to CONFIG_CHANGED
      and reload their local copies — no polling, no restart required
    """

    def __init__(
        self,
        session_factory: Callable[[], async_sessionmaker[AsyncSession]],
        bus: MessageBus,
    ) -> None:
        self._factory = session_factory
        self._bus = bus
        self._cache: TTLCache = TTLCache(maxsize=_CACHE_MAX, ttl=_CACHE_TTL)

    async def initialize(self) -> None:
        """Warm the cache at startup."""
        async with self._factory()() as session:
            cameras = (await session.execute(select(Camera))).scalars().all()
            zones = (await session.execute(select(Zone))).scalars().all()
            rules = (await session.execute(select(Rule))).scalars().all()
        for cam in cameras:
            self._cache[f"camera:{cam.id}"] = cam
        for zone in zones:
            self._cache[f"zone:{zone.id}"] = zone
        for rule in rules:
            self._cache[f"rule:{rule.id}"] = rule
        logger.info(
            "ConfigService initialised: %d cameras, %d zones, %d rules",
            len(cameras), len(zones), len(rules),
        )

    # ── Cameras ───────────────────────────────────────────────────────────────

    async def get_camera(self, camera_id: int) -> Camera | None:
        key = f"camera:{camera_id}"
        if key in self._cache:
            return self._cache[key]
        async with self._factory()() as session:
            cam = await session.get(Camera, camera_id)
        self._cache[key] = cam
        return cam

    async def get_active_cameras(self) -> list[Camera]:
        async with self._factory()() as session:
            result = await session.execute(select(Camera).where(Camera.is_active.is_(True)))
            return list(result.scalars().all())

    async def update_camera(self, camera_id: int, data: dict[str, Any], actor: str) -> Camera | None:
        async with self._factory()() as session:
            cam = await session.get(Camera, camera_id)
            if cam is None:
                return None
            for k, v in data.items():
                if hasattr(cam, k):
                    setattr(cam, k, v)
            await session.commit()
            await session.refresh(cam)
        self._cache[f"camera:{camera_id}"] = cam
        await self._notify("camera", camera_id, actor, data)
        return cam

    # ── Zones ─────────────────────────────────────────────────────────────────

    async def get_zone(self, zone_id: int) -> Zone | None:
        key = f"zone:{zone_id}"
        if key in self._cache:
            return self._cache[key]
        async with self._factory()() as session:
            zone = await session.get(Zone, zone_id)
        self._cache[key] = zone
        return zone

    async def update_zone(self, zone_id: int, data: dict[str, Any], actor: str) -> Zone | None:
        async with self._factory()() as session:
            zone = await session.get(Zone, zone_id)
            if zone is None:
                return None
            for k, v in data.items():
                if hasattr(zone, k):
                    setattr(zone, k, v)
            await session.commit()
            await session.refresh(zone)
        self._cache[f"zone:{zone_id}"] = zone
        await self._notify("zone", zone_id, actor, data)
        return zone

    # ── Rules ─────────────────────────────────────────────────────────────────

    async def get_rule(self, rule_id: int) -> Rule | None:
        key = f"rule:{rule_id}"
        if key in self._cache:
            return self._cache[key]
        async with self._factory()() as session:
            rule = await session.get(Rule, rule_id)
        self._cache[key] = rule
        return rule

    async def get_active_rules(self) -> list[Rule]:
        async with self._factory()() as session:
            result = await session.execute(select(Rule).where(Rule.is_active.is_(True)))
            return list(result.scalars().all())

    async def update_rule(self, rule_id: int, data: dict[str, Any], actor: str) -> Rule | None:
        async with self._factory()() as session:
            rule = await session.get(Rule, rule_id)
            if rule is None:
                return None
            for k, v in data.items():
                if hasattr(rule, k):
                    setattr(rule, k, v)
            await session.commit()
            await session.refresh(rule)
        self._cache[f"rule:{rule_id}"] = rule
        await self._notify("rule", rule_id, actor, data)
        return rule

    async def invalidate(self, scope: str, entity_id: int | None = None) -> None:
        """Force cache miss on next access."""
        if entity_id is not None:
            self._cache.pop(f"{scope}:{entity_id}", None)
        else:
            keys = [k for k in self._cache if k.startswith(f"{scope}:")]
            for k in keys:
                self._cache.pop(k, None)

    # ── Internal ─────────────────────────────────────────────────────────────

    async def _notify(self, scope: str, entity_id: int, actor: str, changes: dict) -> None:
        payload = ConfigChangedPayload(
            scope=scope, entity_id=entity_id, changed_by=actor, changes=changes
        )
        msg = MTPMessage(
            msg_type=MTPMsgType.CONFIG_CHANGED,
            payload=payload.model_dump(),
            priority=MTPPriority.NORMAL,
            source="config_service",
        )
        await self._bus.publish(msg)
