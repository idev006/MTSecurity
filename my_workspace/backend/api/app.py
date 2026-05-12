"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

    from config import Settings
    from protocol.message_bus import MessageBus
    from ssot.config_service import ConfigService
    from ssot.state_registry import StateRegistry

_PREFIX = "/api/v1"


def create_app(
    cfg: "Settings",
    config_svc: "ConfigService",
    state_reg: "StateRegistry",
    bus: "MessageBus",
    engine: "AsyncEngine | None" = None,
) -> FastAPI:
    from api.middleware.audit import AuditMiddleware
    from api.routers import auth, cameras, events, health, rules, users, zones
    from api.websocket.hub import WebSocketHub
    from api.websocket.router import router as ws_router

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        state_reg.set_boot_state("RUNNING")
        yield
        state_reg.set_boot_state("STOPPING")

    app = FastAPI(
        title=cfg.app_name,
        version=cfg.app_version,
        lifespan=lifespan,
        docs_url="/api/docs" if cfg.debug else None,
        redoc_url="/api/redoc" if cfg.debug else None,
        openapi_url="/api/openapi.json" if cfg.debug else None,
    )

    # ── Rate limiter ──────────────────────────────────────────────────────────
    limiter = Limiter(key_func=get_remote_address, default_limits=[cfg.rate_limit_api])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── CORS ──────────────────────────────────────────────────────────────────
    # In debug mode, add common Vite dev-server origins automatically.
    # In production, set CORS_ORIGINS="https://yourdomain.com" in .env.
    origins: list[str] = [o.strip() for o in cfg.cors_origins.split(",") if o.strip()]
    if cfg.debug:
        origins = list({*origins, "http://localhost:5173", "http://localhost:4173"})
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Audit middleware ──────────────────────────────────────────────────────
    app.add_middleware(AuditMiddleware)

    # ── Shared state ──────────────────────────────────────────────────────────
    app.state.config_svc = config_svc
    app.state.state_reg = state_reg
    app.state.bus = bus
    app.state.cfg = cfg

    # ── WebSocket hub ─────────────────────────────────────────────────────────
    hub = WebSocketHub()
    hub.register(bus)
    app.state.ws_hub = hub

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router, prefix=_PREFIX)
    app.include_router(auth.router,   prefix=_PREFIX)
    app.include_router(cameras.router, prefix=_PREFIX)
    app.include_router(zones.router,   prefix=_PREFIX)
    app.include_router(rules.router,   prefix=_PREFIX)
    app.include_router(events.router,  prefix=_PREFIX)
    app.include_router(users.router,   prefix=_PREFIX)
    app.include_router(ws_router,      prefix=_PREFIX)

    return app
