"""Cameras router — CRUD + runtime status + webcam probe."""

from __future__ import annotations

import asyncio
import logging
import sys

import cv2
from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from api.deps import CurrentUser, DBDep, require
from models.camera import Camera
from schemas.camera import CameraCreate, CameraRead, CameraStatus, CameraUpdate, WebcamDevice

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cameras", tags=["cameras"])

_WEBCAM_BACKEND = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY


def _encrypt(url: str, key: str) -> str:
    return Fernet(key.encode()).encrypt(url.encode()).decode()


# ── Webcam probe (blocking I/O — run in executor) ────────────────────────────

def _probe_webcams() -> list[WebcamDevice]:
    """Check device indices 0-9 synchronously (called via run_in_executor)."""
    found: list[WebcamDevice] = []
    for i in range(10):
        cap = cv2.VideoCapture(i, _WEBCAM_BACKEND)
        if cap.isOpened():
            found.append(WebcamDevice(index=i, label=f"Webcam {i}"))
        cap.release()
    return found


@router.get("/webcams", response_model=list[WebcamDevice],
            dependencies=[require("cameras:read")])
async def list_available_webcams() -> list[WebcamDevice]:
    """Probe local device indices 0-9 and return available webcams."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _probe_webcams)


# ── List ──────────────────────────────────────────────────────────────────────

@router.get("", response_model=list[CameraRead], dependencies=[require("cameras:read")])
async def list_cameras(db: DBDep, user: CurrentUser) -> list[Camera]:
    result = await db.execute(select(Camera).order_by(Camera.id))
    cameras = result.scalars().all()
    allowed = user.camera_ids()
    if allowed is not None:
        cameras = [c for c in cameras if c.id in allowed]
    return list(cameras)


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("", response_model=CameraRead, status_code=status.HTTP_201_CREATED,
             dependencies=[require("cameras:create")])
async def create_camera(body: CameraCreate, request: Request, db: DBDep, user: CurrentUser) -> Camera:
    cfg = request.app.state.cfg

    if body.source_type == "rtsp":
        encrypted = _encrypt(body.rtsp_url, cfg.encryption_key.get_secret_value())
        cam = Camera(
            name=body.name,
            source_type="rtsp",
            rtsp_url_encrypted=encrypted,
            device_index=None,
            location=body.location,
            resolution_width=body.resolution_width,
            resolution_height=body.resolution_height,
            fps=body.fps,
        )
    else:  # webcam
        # Reject duplicate device_index across active cameras
        result = await db.execute(
            select(Camera).where(Camera.device_index == body.device_index,
                                 Camera.is_active == True)  # noqa: E712
        )
        if result.scalars().first():
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Webcam device index {body.device_index} is already registered to an active camera",
            )
        cam = Camera(
            name=body.name,
            source_type="webcam",
            rtsp_url_encrypted=None,
            device_index=body.device_index,
            location=body.location,
            resolution_width=body.resolution_width,
            resolution_height=body.resolution_height,
            fps=body.fps,
        )

    db.add(cam)
    await db.flush()
    await db.refresh(cam)
    await db.commit()

    config_svc = request.app.state.config_svc
    await config_svc.invalidate("camera")

    logger.info(
        "Camera created: id=%d name=%s source=%s by=%s",
        cam.id, cam.name, cam.source_type, user.username,
    )
    return cam


# ── Read ──────────────────────────────────────────────────────────────────────

@router.get("/{camera_id}", response_model=CameraRead, dependencies=[require("cameras:read")])
async def get_camera(camera_id: int, db: DBDep, user: CurrentUser) -> Camera:
    cam = await db.get(Camera, camera_id)
    if cam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    allowed = user.camera_ids()
    if allowed is not None and camera_id not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied")
    return cam


# ── Update ────────────────────────────────────────────────────────────────────

@router.patch("/{camera_id}", response_model=CameraRead, dependencies=[require("cameras:update")])
async def update_camera(
    camera_id: int, body: CameraUpdate, request: Request, db: DBDep, user: CurrentUser
) -> Camera:
    config_svc = request.app.state.config_svc
    data = body.model_dump(exclude_none=True)
    cam = await config_svc.update_camera(camera_id, data, actor=user.username)
    if cam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    return cam


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[require("cameras:delete")])
async def delete_camera(camera_id: int, request: Request, db: DBDep, user: CurrentUser) -> None:
    cam = await db.get(Camera, camera_id)
    if cam is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Camera not found")
    await db.delete(cam)
    await db.commit()
    await request.app.state.config_svc.invalidate("camera", camera_id)
    logger.info("Camera deleted: id=%d by=%s", camera_id, user.username)


# ── Status ────────────────────────────────────────────────────────────────────

@router.get("/{camera_id}/status", response_model=CameraStatus,
            dependencies=[require("cameras:read")])
async def camera_status(camera_id: int, request: Request, user: CurrentUser) -> CameraStatus:
    state_reg = request.app.state.state_reg
    cam_state = state_reg.get_camera_state(camera_id)
    return CameraStatus(
        camera_id=camera_id,
        state=cam_state.state,
        fps=cam_state.fps,
        latency_ms=cam_state.latency_ms,
        last_frame_at=cam_state.last_frame_at,
        error_msg=cam_state.error_msg,
    )
