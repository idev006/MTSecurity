"""MTSecurity v2 — boot orchestrator."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

import uvicorn

from config import get_settings
from db.init_db import create_tables
from db.pragmas import apply_pragmas
from db.session import get_session_factory, init_engine
from ingestion.camera_manager import CameraManager
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mtsecurity.main")


async def bootstrap() -> None:
    cfg = get_settings()
    cfg.ensure_dirs()

    logger.info("MTSecurity v%s starting — env=%s", cfg.app_version, cfg.environment)
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
    frame_buffer = FrameBuffer()
    cam_manager = CameraManager(
        buffer=frame_buffer,
        config_svc=config_svc,
        state_reg=state_reg,
        bus=bus,
        encryption_key=cfg.encryption_key.get_secret_value().encode(),
    )
    await cam_manager.start_all()
    logger.info("CameraManager started — %d camera(s) active", cam_manager.active_count)

    # ── 5b. Webcam Hotplug Watcher ─────────────────────────────────────────────────
    loop = asyncio.get_running_loop()
    webcam_watcher = WebcamWatcher(
        cam_manager=cam_manager,
        config_svc=config_svc,
        state_reg=state_reg,
        loop=loop,
        interval=15,
    )
    webcam_watcher.start()

    # ── 5. AI Pipeline ───────────────────────────────────────────────────────
    model_reg = ModelRegistry(device=cfg.model_device)
    inference_engine = InferenceEngine(model_reg, "yolov11n", cfg.model_path)
    ai_pipeline = AIPipeline(
        buffer=frame_buffer,
        engine=inference_engine,
        bus=bus,
        confidence_threshold=cfg.ai_confidence_threshold,
    )
    ai_pipeline.start(loop)

    # ── 5c. Rules + Alerts Pipeline ───────────────────────────────────────────────
    dispatcher = NotificationDispatcher()
    # Notification channels are added dynamically from settings (Phase 3+)

    alert_manager = AlertManager(
        dispatcher=dispatcher,
        config_svc=config_svc,
        bus=bus,
        base_url=cfg.base_url,
        session_factory=get_session_factory(),
        frame_buffer=frame_buffer,
        snapshot_dir=cfg.snapshot_dir,
    )
    alert_manager.register(bus)

    rule_engine = RuleEngine(config_svc=config_svc, bus=bus)
    await rule_engine.initialize()
    rule_engine.register(bus)
    logger.info("RuleEngine + AlertManager started")

    # ── 5. API Core ──────────────────────────────────────────────────────────
    state_reg.set_boot_state("STARTING_API")
    from api.app import create_app
    app = create_app(cfg, config_svc, state_reg, bus, engine)
    app.state.cam_manager = cam_manager
    app.state.frame_buffer = frame_buffer
    app.state.rule_engine = rule_engine
    app.state.alert_manager = alert_manager

    state_reg.set_boot_state("RUNNING")
    logger.info("All services up — listening on %s:%s", cfg.host, cfg.port)

    uv_config = uvicorn.Config(
        app,
        host=cfg.host,
        port=cfg.port,
        log_level="info",
        access_log=cfg.debug,
    )
    server = uvicorn.Server(uv_config)

    # add_signal_handler is Unix-only; uvicorn handles Ctrl+C on Windows natively
    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, server.handle_exit, sig, None)

    await server.serve()

    # ── Graceful shutdown ────────────────────────────────────────────────────
    logger.info("Shutting down…")
    state_reg.set_boot_state("SHUTTING_DOWN")
    webcam_watcher.stop()
    ai_pipeline.stop()
    await cam_manager.stop_all()
    await bus.stop()
    await engine.dispose()
    logger.info("Shutdown complete")


def main() -> None:
    try:
        asyncio.run(bootstrap())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
