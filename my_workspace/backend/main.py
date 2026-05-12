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
from protocol.message_bus import MessageBus
from ssot.config_service import ConfigService
from ssot.state_registry import StateRegistry

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

    # ── 4. API Core ──────────────────────────────────────────────────────────
    state_reg.set_boot_state("STARTING_API")
    from api.app import create_app
    app = create_app(cfg, config_svc, state_reg, bus, engine)

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
