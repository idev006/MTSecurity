import asyncio
import logging
import sys

from cryptography.fernet import Fernet
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from api.deps import CurrentUser, DBDep, require
from ingestion.webcam_enumerator import EnumeratedDevice, enumerate_webcams
from models.camera import Camera
from schemas.camera import CameraCreate, CameraRead, CameraStatus, CameraUpdate, WebcamDevice

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cameras", tags=["cameras"])

_WEBCAM_BACKEND = None  # handled inside webcam_enumerator


def _encrypt(url: str, key: str) -> str:
    return Fernet(key.encode()).encrypt(url.encode()).decode()


# ── Webcam probe (blocking I/O — run in executor) ────────────────────────────

@router.get("/webcams", response_model=list[WebcamDevice],
            dependencies=[require("cameras:read")])
async def list_available_webcams() -> list[WebcamDevice]:
    """Probe local device indices 0-9 and return available webcams with device_name."""
    loop = asyncio.get_running_loop()
    devices = await loop.run_in_executor(None, enumerate_webcams)
    return [
        WebcamDevice(index=d.index, label=d.label, device_name=d.device_name)
        for d in devices
    ]


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
            device_name=None,
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
            device_name=body.device_name,  # store fingerprint
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

    # Start camera thread immediately (invalidate does not publish CONFIG_CHANGED)
    cam_manager = request.app.state.cam_manager
    await cam_manager.start_camera(cam.id)

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
    config_svc = request.app.state.config_svc
    await config_svc.invalidate("camera", camera_id)
    await config_svc.notify("camera", camera_id, {"deleted": True}, actor=user.username)
    request.app.state.cam_manager.stop_camera(camera_id)
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


# ── MJPEG stream ──────────────────────────────────────────────────────────────

import asyncio as _asyncio

import jwt as _jwt
from fastapi import Query as _Query
from fastapi.responses import StreamingResponse


@router.get("/{camera_id}/stream")
async def mjpeg_stream(
    camera_id: int,
    request: Request,
    token: str = _Query(..., description="JWT access token (same as ?token= used for WebSocket)"),
) -> StreamingResponse:
    """Push a continuous MJPEG stream from FrameBuffer.

    Auth is via ``?token=<access_token>`` because browser ``<img>`` tags
    cannot send Authorization headers.
    The stream ends automatically when the client disconnects.
    """
    # ── Validate token manually (same as WS endpoint) ────────────────────────
    cfg = request.app.state.cfg
    try:
        payload = _jwt.decode(
            token,
            cfg.jwt_secret_key.get_secret_value(),
            algorithms=[cfg.jwt_algorithm],
        )
    except _jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except _jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong token type")

    # ── Stream frames ─────────────────────────────────────────────────────────
    frame_buffer = request.app.state.frame_buffer

    async def generate():
        boundary = b"--frame\r\nContent-Type: image/jpeg\r\n\r\n"
        last_data: bytes | None = None
        try:
            while True:
                if await request.is_disconnected():
                    break
                frame = frame_buffer.get(camera_id)
                if frame is None:
                    await _asyncio.sleep(0.05)
                    continue
                # Skip duplicate frame (camera hasn't produced a new one yet)
                if frame.data is last_data:
                    await _asyncio.sleep(1 / 30)
                    continue
                last_data = frame.data
                yield boundary + frame.data + b"\r\n"
                await _asyncio.sleep(1 / 30)  # cap at 30 fps
        except _asyncio.CancelledError:
            pass  # client disconnected cleanly
        except Exception:
            logger.exception("MJPEG stream error camera_id=%d", camera_id)

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

