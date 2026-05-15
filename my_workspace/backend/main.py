"""MTSecurity v2 — entry point.

Usage
-----
Normal (production):
    python main.py

Dev with auto-reload:
    python main.py --reload

Override host/port:
    python main.py --host 0.0.0.0 --port 9000

All service initialisation is performed inside the FastAPI lifespan
(api/app.py) so --reload works correctly: uvicorn can re-import the
module without restarting background services prematurely.
"""

from __future__ import annotations

import argparse
import logging

import uvicorn

from config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mtsecurity.main")

# Directories that uvicorn watches for changes in --reload mode.
_RELOAD_DIRS = [
    ".",
    "api",
    "rules",
    "alerts",
    "ingestion",
    "ai",
    "ssot",
    "protocol",
    "auth",
    "db",
    "schemas",
    "models",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="MTSecurity v2 server")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload on code changes (dev mode only)",
    )
    parser.add_argument("--host", default=None, help="Override host from settings")
    parser.add_argument("--port", type=int, default=None, help="Override port from settings")
    args = parser.parse_args()

    cfg = get_settings()
    host = args.host or cfg.host
    port = args.port or cfg.port

    if args.reload:
        logger.info("Starting in DEV mode with --reload (watching %d dirs)", len(_RELOAD_DIRS))

    uvicorn.run(
        "api.app:app",          # string import — required for --reload to work
        host=host,
        port=port,
        reload=args.reload,
        reload_dirs=_RELOAD_DIRS if args.reload else None,
        log_level="info",
        access_log=cfg.debug or args.reload,
    )


if __name__ == "__main__":
    main()
