"""FastAPI application factory — all services initialised in lifespan."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

logger = logging.getLogger("mtsecurity.app")

_PREFIX = "/api/v1"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """Start every service on startup; tear down gracefully on shutdown."""
    from config import get_settings
    from db.init_db import create_tables
    from db.pragmas import apply_pragmas
    from db.session import get_session_factory, init_engine
    from ingestion.camera_manager import CameraManager
    from ingestion.clip_buffer import ClipBuffer
    from ingestion.frame_buffer import FrameBuffer
    from ingestion.webcam_watcher import WebcamWatcher
    from alerts.alert_manager import AlertManager
    from alerts.notifications.dispatcher import NotificationDispatcher
    from rules.rule_engine import RuleEngine
    from protocol.message_bus import MessageBus
    from ssot.config_service import ConfigService
    from ssot.state_registry import StateRegistry
    from ai.model_registry import ModelRegistry
    from ai.inference_engine import InferenceEngine
    from ai.pipeline import AIPipeline
    from api.websocket.hub import WebSocketHub

    cfg = get_settings()
    cfg.ensure_dirs()
    logger.info("MTSecurity v%s starting — env=%s", cfg.app_version, cfg.environment)

    # Install a global asyncio exception handler so silently-crashed Tasks
    # (the default just prints to stderr and swallows the traceback) get
    # properly logged.  This is the #1 debugging tool for concurrent crashes.
    def _asyncio_exc_handler(loop, context):
        exc = context.get("exception")
        msg = context.get("message", "unknown asyncio error")
        if exc is not None:
            logger.error("Unhandled asyncio exception — %s", msg, exc_info=exc)
        else:
            logger.error("Unhandled asyncio error — %s | context=%s", msg, context)
    asyncio.get_running_loop().set_exception_handler(_asyncio_exc_handler)

    state_reg = StateRegistry()
    state_reg.set_boot_state("INITIALIZING")

    # ── 1. Protocol Layer ────────────────────────────────────────────────────
    state_reg.set_boot_state("STARTING_SERVICES")
    bus = MessageBus()
    await bus.start()
    logger.info("MessageBus started")

    # ── 2. Database ──────────────────────────────────────────────────────────
    engine = init_engine(cfg.database_url)
    apply_pragmas(engine)
    await create_tables(engine)

    # ── 3. SSOT Layer ────────────────────────────────────────────────────────
    config_svc = ConfigService(get_session_factory, bus)
    await config_svc.initialize()

    # ── 4. Ingestion Layer ───────────────────────────────────────────────────
    # Read evidence quality settings from DB (applied at CameraThread startup)
    from models.system_setting import SystemSetting as _SystemSetting
    from sqlalchemy import select as _sa_select
    async with get_session_factory()() as _db:
        _rows = (await _db.execute(_sa_select(_SystemSetting))).scalars().all()
        _settings_map = {r.key: r.value for r in _rows}
    evidence_tier = _settings_map.get("evidence_tier", "DETAIL")
    stream_tier   = _settings_map.get("stream_tier", "MONITOR")
    clip_crf = int(_settings_map.get("clip_crf", "23"))
    logger.info("Quality: stream=%s evidence=%s crf=%d", stream_tier, evidence_tier, clip_crf)

    frame_buffer  = FrameBuffer()
    hires_buffer  = FrameBuffer()           # evidence frames for snapshot + clip
    stream_buffer = FrameBuffer()           # stream frames for MJPEG endpoint
    clip_buffer   = ClipBuffer(max_frames=150)   # ~10 s @ 15 fps
    cam_manager = CameraManager(
        buffer=frame_buffer,
        config_svc=config_svc,
        state_reg=state_reg,
        bus=bus,
        encryption_key=cfg.encryption_key.get_secret_value().encode(),
        clip_buffer=clip_buffer,
        hires_buffer=hires_buffer,
        evidence_tier=evidence_tier,
        stream_buffer=stream_buffer,
        stream_tier=stream_tier,
    )
    await cam_manager.start_all()
    logger.info("CameraManager started — %d camera(s) active", cam_manager.active_count)

    # ── 5. Webcam Hotplug Watcher ────────────────────────────────────────────
    loop = asyncio.get_running_loop()
    webcam_watcher = WebcamWatcher(
        cam_manager=cam_manager,
        config_svc=config_svc,
        state_reg=state_reg,
        loop=loop,
        interval=15,
    )
    webcam_watcher.start()

    # ── 6. AI Pipeline ───────────────────────────────────────────────────────
    # compile_model() is a blocking CPU-bound call — run off the event loop
    model_reg = ModelRegistry(device=cfg.model_device)
    inference_engine = await loop.run_in_executor(
        None, lambda: InferenceEngine(model_reg, "yolov11n", cfg.model_path)
    )
    ai_pipeline = AIPipeline(
        buffer=frame_buffer,
        engine=inference_engine,
        bus=bus,
        confidence_threshold=cfg.ai_confidence_threshold,
        target_classes=cfg.ai_target_classes,
    )
    ai_pipeline.start(loop)

    # ── 7. Rules + Alerts Pipeline ───────────────────────────────────────────
    dispatcher = NotificationDispatcher()
    alert_manager = AlertManager(
        dispatcher=dispatcher,
        config_svc=config_svc,
        bus=bus,
        base_url=cfg.base_url,
        session_factory=get_session_factory(),
        frame_buffer=frame_buffer,
        snapshot_dir=cfg.snapshot_dir,
        clip_buffer=clip_buffer,
        clip_dir=cfg.clip_dir,
        ffmpeg_path=cfg.ffmpeg_path,
        clip_width=cfg.clip_width,
        clip_height=cfg.clip_height,
        hires_buffer=hires_buffer,
        default_clip_crf=clip_crf,
    )
    alert_manager.register(bus)

    rule_engine = RuleEngine(config_svc=config_svc, bus=bus)
    await rule_engine.initialize()
    rule_engine.register(bus)
    logger.info("RuleEngine + AlertManager started")

    # ── 8. WebSocket hub ─────────────────────────────────────────────────────
    hub = WebSocketHub()
    hub.register(bus)

    # ── Attach everything to app.state ───────────────────────────────────────
    app.state.cfg = cfg
    app.state.config_svc = config_svc
    app.state.state_reg = state_reg
    app.state.bus = bus
    app.state.ws_hub = hub
    app.state.cam_manager = cam_manager
    app.state.frame_buffer  = frame_buffer
    app.state.hires_buffer  = hires_buffer
    app.state.stream_buffer = stream_buffer
    app.state.rule_engine = rule_engine
    app.state.alert_manager = alert_manager

    state_reg.set_boot_state("RUNNING")
    logger.info("All services up — ready to serve requests")

    # ── Application is running ───────────────────────────────────────────────
    yield

    # ── Graceful shutdown ────────────────────────────────────────────────────
    logger.info("Shutting down…")
    state_reg.set_boot_state("STOPPING")
    webcam_watcher.stop()
    ai_pipeline.stop()
    await cam_manager.stop_all()
    await bus.stop()
    await engine.dispose()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create the FastAPI application.

    All heavy service initialisation happens inside the lifespan context so
    that ``uvicorn --reload`` can safely re-import this module without
    re-starting background services prematurely.
    """
    from config import get_settings
    from api.middleware.audit import AuditMiddleware
    from api.routers import auth, cameras, events, health, lpr, rules, users, zones
    from api.routers.system import router as system_router
    from api.routers.simulate import router as simulate_router
    from api.websocket.router import router as ws_router

    cfg = get_settings()

    application = FastAPI(
        title=cfg.app_name,
        version=cfg.app_version,
        lifespan=_lifespan,
        docs_url="/api/docs" if cfg.debug else None,
        redoc_url="/api/redoc" if cfg.debug else None,
        openapi_url="/api/openapi.json" if cfg.debug else None,
    )

    # ── Rate limiter ──────────────────────────────────────────────────────────
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=[cfg.rate_limit_api],
    )
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── CORS ──────────────────────────────────────────────────────────────────
    origins: list[str] = [o.strip() for o in cfg.cors_origins.split(",") if o.strip()]
    if cfg.debug:
        origins = list({*origins, "http://localhost:5173", "http://localhost:4173"})
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(AuditMiddleware)

    # ── Routers ───────────────────────────────────────────────────────────────
    application.include_router(health.router,    prefix=_PREFIX)
    application.include_router(auth.router,      prefix=_PREFIX)
    application.include_router(cameras.router,   prefix=_PREFIX)
    application.include_router(zones.router,     prefix=_PREFIX)
    application.include_router(rules.router,     prefix=_PREFIX)
    application.include_router(events.router,    prefix=_PREFIX)
    application.include_router(lpr.router,       prefix=_PREFIX)
    application.include_router(users.router,     prefix=_PREFIX)
    application.include_router(system_router,    prefix=_PREFIX)
    application.include_router(simulate_router,  prefix=_PREFIX)
    application.include_router(ws_router,        prefix=_PREFIX)

    return application


# Module-level app instance — required for ``uvicorn "api.app:app" --reload``
app = create_app()
