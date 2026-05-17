"""Zones router — CRUD zones per camera."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from api.deps import CurrentUser, DBDep, require
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
