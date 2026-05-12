"""Events router — list, filter, acknowledge, silence, escalate, notes."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from api.deps import CurrentUser, DBDep, require
from models.alert_note import AlertNote
from models.event import Event
from schemas.event import (
    AlertAckRequest,
    AlertEscalateRequest,
    AlertNoteCreate,
    AlertSilenceRequest,
    EventFilter,
    EventRead,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["events"])


def _snapshot_url(base_url: str, path: str | None, event_id: int) -> str | None:
    if path is None:
        return None
    return f"{base_url.rstrip('/')}/api/v1/events/{event_id}/snapshot"


def _to_read(event: Event, base_url: str) -> dict:
    d = {c.name: getattr(event, c.name) for c in event.__table__.columns}
    d["snapshot_url"] = _snapshot_url(base_url, event.snapshot_path, event.id)
    d["clip_url"] = None
    return d


# ── List / filter ─────────────────────────────────────────────────────────────

@router.get("", response_model=list[EventRead], dependencies=[require("events:read")])
async def list_events(request: Request, db: DBDep, user: CurrentUser, f: EventFilter = None) -> list[dict]:
    if f is None:
        f = EventFilter()
    base_url: str = request.app.state.cfg.base_url

    query = select(Event).order_by(Event.occurred_at.desc())

    # Scope filter
    allowed = user.camera_ids()
    if allowed is not None:
        query = query.where(Event.camera_id.in_(allowed))

    if f.camera_id is not None:
        query = query.where(Event.camera_id == f.camera_id)
    if f.behavior is not None:
        query = query.where(Event.behavior == f.behavior)
    if f.severity is not None:
        query = query.where(Event.severity == f.severity)
    if f.status is not None:
        query = query.where(Event.status == f.status)
    if f.from_dt is not None:
        query = query.where(Event.occurred_at >= f.from_dt)
    if f.to_dt is not None:
        query = query.where(Event.occurred_at <= f.to_dt)

    offset = (f.page - 1) * f.page_size
    query = query.offset(offset).limit(f.page_size)

    result = await db.execute(query)
    return [_to_read(e, base_url) for e in result.scalars().all()]


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
