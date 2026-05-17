"""Zones router — CRUD zones per camera."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from api.deps import CurrentUser, DBDep, require
from models.rule import Rule
from models.zone import Zone
from schemas.zone import ZoneCreate, ZoneRead, ZoneUpdate

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/zones", tags=["zones"])


@router.get("", response_model=list[ZoneRead], dependencies=[require("zones:read")])
async def list_zones(db: DBDep, camera_id: int | None = None) -> list[Zone]:
    query = select(Zone).order_by(Zone.camera_id, Zone.id)
    if camera_id is not None:
        query = query.where(Zone.camera_id == camera_id)
    result = await db.execute(query)
    return list(result.scalars().all())


@router.post("", response_model=ZoneRead, status_code=status.HTTP_201_CREATED,
             dependencies=[require("zones:create")])
async def create_zone(body: ZoneCreate, request: Request, db: DBDep, user: CurrentUser) -> Zone:
    coords_json = json.dumps(body.coordinates)
    zone = Zone(
        camera_id=body.camera_id,
        name=body.name,
        coordinates=coords_json,
        color=body.color,
    )
    db.add(zone)
    await db.flush()
    await db.refresh(zone)
    await db.commit()
    await request.app.state.config_svc.invalidate("zone")
    logger.info("Zone created: id=%d cam=%d by=%s", zone.id, zone.camera_id, user.username)
    return zone


@router.get("/{zone_id}", response_model=ZoneRead, dependencies=[require("zones:read")])
async def get_zone(zone_id: int, db: DBDep) -> Zone:
    zone = await db.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone not found")
    return zone


@router.patch("/{zone_id}", response_model=ZoneRead, dependencies=[require("zones:update")])
async def update_zone(
    zone_id: int, body: ZoneUpdate, request: Request, db: DBDep, user: CurrentUser
) -> Zone:
    data = body.model_dump(exclude_none=True)
    if "coordinates" in data:
        data["coordinates"] = json.dumps(data["coordinates"])
    zone = await request.app.state.config_svc.update_zone(zone_id, data, actor=user.username)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone not found")
    return zone


@router.delete("/{zone_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[require("zones:delete")])
async def delete_zone(zone_id: int, request: Request, db: DBDep, user: CurrentUser) -> None:
    zone = await db.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone not found")
    await db.delete(zone)
    await db.commit()
    config_svc = request.app.state.config_svc
    await config_svc.invalidate("zone", zone_id)
    await config_svc.notify("zone", zone_id, {"deleted": True}, actor=user.username)
    logger.info("Zone deleted: id=%d by=%s", zone_id, user.username)


# ── Enable / Disable (cascade to rules) ──────────────────────────────────────

async def _zone_set_active(
    zone_id: int,
    active: bool,
    request: Request,
    db: DBDep,
    user: CurrentUser,
) -> Zone:
    zone = await db.get(Zone, zone_id)
    if zone is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Zone not found")

    previous = zone.is_active
    if previous == active:
        return zone  # no-op — already in desired state

    # Load child rules for cascade
    rules_result = await db.execute(select(Rule).where(Rule.zone_id == zone_id))
    child_rules = rules_result.scalars().all()

    # Apply all changes in one commit
    zone.is_active = active
    for rule in child_rules:
        rule.is_active = active

    await db.commit()
    await db.refresh(zone)

    # Propagate config changes for zone and all cascaded rules
    config_svc = request.app.state.config_svc
    await config_svc.invalidate("zone", zone_id)
    await config_svc.notify("zone", zone_id, {"is_active": active}, actor=user.username)
    for rule in child_rules:
        await db.refresh(rule)
        await config_svc.invalidate("rule", rule.id)
        await config_svc.notify("rule", rule.id, {"is_active": active}, actor=user.username)

    logger.info("Zone %d (%s) %s by %s — cascaded %d rules",
                zone_id, zone.name, "enabled" if active else "disabled", user.username,
                len(child_rules))
    return zone


@router.post("/{zone_id}/enable", response_model=ZoneRead,
             dependencies=[require("zones:update")])
async def enable_zone(zone_id: int, request: Request, db: DBDep, user: CurrentUser) -> Zone:
    """Enable a zone and all its rules."""
    return await _zone_set_active(zone_id, True, request, db, user)


@router.post("/{zone_id}/disable", response_model=ZoneRead,
             dependencies=[require("zones:update")])
async def disable_zone(zone_id: int, request: Request, db: DBDep, user: CurrentUser) -> Zone:
    """Disable a zone and all its rules."""
    return await _zone_set_active(zone_id, False, request, db, user)
