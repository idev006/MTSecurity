"""Events router — list, filter, acknowledge, silence, escalate, notes, delete."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select

from api.deps import CurrentUser, DBDep, require
from models.alert_note import AlertNote
from models.event import Event
from schemas.event import (
    AlertAckRequest,
    AlertEscalateRequest,
    AlertNoteCreate,
    AlertSilenceRequest,
    EventFilter,
    EventPage,
    EventPurgeRequest,
    EventPurgeResponse,
    EventRead,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["events"])


def _snapshot_url(base_url: str, path: str | None, event_id: int) -> str | None:
    if path is None:
        return None
    return f"{base_url.rstrip('/')}/api/v1/events/{event_id}/snapshot"


def _clip_url(base_url: str, path: str | None, event_id: int) -> str | None:
    if path is None:
        return None
    return f"{base_url.rstrip('/')}/api/v1/events/{event_id}/clip"


def _to_read(event: Event, base_url: str) -> dict:
    d = {c.name: getattr(event, c.name) for c in event.__table__.columns}
    d["snapshot_url"] = _snapshot_url(base_url, event.snapshot_path, event.id)
    d["clip_url"] = _clip_url(base_url, event.clip_path, event.id)
    return d


# ── List / filter ─────────────────────────────────────────────────────────────

@router.get("", response_model=EventPage, dependencies=[require("events:read")])
async def list_events(request: Request, db: DBDep, user: CurrentUser, f: EventFilter = Depends()) -> dict:
    base_url: str = request.app.state.cfg.base_url

    base_query = select(Event)

    # Scope filter
    allowed = user.camera_ids()
    if allowed is not None:
        base_query = base_query.where(Event.camera_id.in_(allowed))

    if f.camera_id is not None:
        base_query = base_query.where(Event.camera_id == f.camera_id)
    if f.behavior is not None:
        base_query = base_query.where(Event.behavior == f.behavior)
    if f.severity is not None:
        base_query = base_query.where(Event.severity == f.severity)
    if f.status is not None:
        base_query = base_query.where(Event.status == f.status)
    if f.from_dt is not None:
        base_query = base_query.where(Event.occurred_at >= f.from_dt)
    if f.to_dt is not None:
        base_query = base_query.where(Event.occurred_at <= f.to_dt)

    count_query = select(func.count()).select_from(base_query.subquery())
    total: int = (await db.execute(count_query)).scalar_one()

    offset = (f.page - 1) * f.page_size
    rows_query = base_query.order_by(Event.occurred_at.desc()).offset(offset).limit(f.page_size)
    result = await db.execute(rows_query)

    return {
        "items": [_to_read(e, base_url) for e in result.scalars().all()],
        "total": total,
        "page": f.page,
        "page_size": f.page_size,
    }


@router.get("/{event_id}", response_model=EventRead, dependencies=[require("events:read")])
async def get_event(event_id: int, request: Request, db: DBDep, user: CurrentUser) -> dict:
    base_url: str = request.app.state.cfg.base_url
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    allowed = user.camera_ids()
    if allowed is not None and event.camera_id not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    return _to_read(event, base_url)


@router.get("/{event_id}/snapshot", dependencies=[require("events:read")])
async def get_snapshot(event_id: int, request: Request, db: DBDep, user: CurrentUser) -> FileResponse:
    event = await db.get(Event, event_id)
    if event is None or not event.snapshot_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Snapshot not found")
    
    allowed = user.camera_ids()
    if allowed is not None and event.camera_id not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
        
    path = request.app.state.cfg.snapshot_dir / event.snapshot_path
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Snapshot file missing on disk")
        
    return FileResponse(path, media_type="image/jpeg")


@router.get("/{event_id}/clip", dependencies=[require("events:read")])
async def get_clip(event_id: int, request: Request, db: DBDep, user: CurrentUser) -> FileResponse:
    event = await db.get(Event, event_id)
    if event is None or not event.clip_path:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clip not found")

    allowed = user.camera_ids()
    if allowed is not None and event.camera_id not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")

    path = request.app.state.cfg.clip_dir / event.clip_path
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Clip file missing on disk")

    return FileResponse(path, media_type="video/mp4")


# ── Acknowledge ───────────────────────────────────────────────────────────────

@router.post("/{event_id}/acknowledge", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=[require("alerts:acknowledge")])
async def acknowledge(event_id: int, body: AlertAckRequest, db: DBDep, user: CurrentUser) -> None:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    event.status = "ACKNOWLEDGED"
    event.acknowledged_at = datetime.now(timezone.utc)
    event.acknowledged_by = user.username
    if body.note:
        db.add(AlertNote(event_id=event_id, author=user.username, body=body.note,
                         created_at=datetime.now(timezone.utc)))
    await db.commit()
    logger.info("Event %d acknowledged by %s", event_id, user.username)


# ── Silence ───────────────────────────────────────────────────────────────────

@router.post("/{event_id}/silence", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=[require("alerts:silence")])
async def silence(event_id: int, body: AlertSilenceRequest, db: DBDep, user: CurrentUser) -> None:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    event.status = "SILENCED"
    event.silenced_until = datetime.now(timezone.utc) + timedelta(seconds=body.duration_seconds)
    await db.commit()
    logger.info("Event %d silenced for %ds by %s", event_id, body.duration_seconds, user.username)


# ── Escalate ──────────────────────────────────────────────────────────────────

@router.post("/{event_id}/escalate", status_code=status.HTTP_204_NO_CONTENT,
             dependencies=[require("alerts:escalate")])
async def escalate(event_id: int, body: AlertEscalateRequest, db: DBDep, user: CurrentUser) -> None:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    event.status = "ESCALATED"
    db.add(AlertNote(event_id=event_id, author=user.username,
                     body=f"[ESCALATED] {body.reason}",
                     created_at=datetime.now(timezone.utc)))
    await db.commit()
    logger.info("Event %d escalated by %s: %s", event_id, user.username, body.reason)


# ── Notes ─────────────────────────────────────────────────────────────────────

@router.post("/{event_id}/notes", status_code=status.HTTP_201_CREATED,
             dependencies=[require("events:read")])
async def add_note(event_id: int, body: AlertNoteCreate, db: DBDep, user: CurrentUser) -> dict:
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    note = AlertNote(event_id=event_id, author=user.username, body=body.body,
                     created_at=datetime.now(timezone.utc))
    db.add(note)
    await db.flush()
    await db.commit()
    return {"id": note.id, "author": note.author, "body": note.body,
            "created_at": note.created_at.isoformat()}


# ── Delete ────────────────────────────────────────────────────────────────────

def _remove_file(base_dir: Path, relative_name: str | None) -> None:
    """Silently remove a snapshot/clip file; ignore errors."""
    if not relative_name:
        return
    try:
        p = base_dir / relative_name
        if p.exists():
            p.unlink()
    except Exception as exc:
        logger.warning("Could not delete file %s: %s", relative_name, exc)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[require("events:delete")])
async def delete_event(event_id: int, request: Request, db: DBDep, user: CurrentUser) -> None:
    """Delete a single event and its snapshot/clip files from disk."""
    event = await db.get(Event, event_id)
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")

    allowed = user.camera_ids()
    if allowed is not None and event.camera_id not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")

    cfg = request.app.state.cfg
    _remove_file(cfg.snapshot_dir, event.snapshot_path)
    _remove_file(cfg.clip_dir, event.clip_path)

    await db.delete(event)
    await db.commit()
    logger.info("Event %d deleted by %s (snapshot=%s clip=%s)",
                event_id, user.username, event.snapshot_path, event.clip_path)


@router.post("/purge", response_model=EventPurgeResponse,
             dependencies=[require("events:delete")])
async def purge_events(
    body: EventPurgeRequest,
    request: Request,
    db: DBDep,
    user: CurrentUser,
) -> dict:
    """
    Bulk-delete events matching the given filters.
    Pass ``dry_run=true`` to preview the count without deleting.
    """
    cfg = request.app.state.cfg

    q = select(Event)
    allowed = user.camera_ids()
    if allowed is not None:
        q = q.where(Event.camera_id.in_(allowed))
    if body.before_dt is not None:
        q = q.where(Event.occurred_at < body.before_dt)
    if body.camera_id is not None:
        q = q.where(Event.camera_id == body.camera_id)
    if body.statuses:
        q = q.where(Event.status.in_(body.statuses))

    result = await db.execute(q)
    events = result.scalars().all()

    if body.dry_run:
        return {"deleted": len(events), "dry_run": True}

    for ev in events:
        _remove_file(cfg.snapshot_dir, ev.snapshot_path)
        _remove_file(cfg.clip_dir, ev.clip_path)
        await db.delete(ev)

    await db.commit()
    logger.info(
        "Purge: %d event(s) deleted by %s (before=%s cam=%s statuses=%s)",
        len(events), user.username, body.before_dt, body.camera_id, body.statuses,
    )
    return {"deleted": len(events), "dry_run": False}
