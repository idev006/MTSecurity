"""Audit middleware — records every mutating request to audit_logs table."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from db.session import get_session_factory
from models.audit_log import AuditLog

logger = logging.getLogger(__name__)

_MUTATING = {"POST", "PUT", "PATCH", "DELETE"}


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        if request.method not in _MUTATING:
            return response
        if not request.url.path.startswith("/api/"):
            return response

        try:
            user = getattr(request.state, "user", None)
            actor = user.username if user else "anonymous"
            user_id = user.id if user else None

            path_parts = request.url.path.strip("/").split("/")
            resource = path_parts[2] if len(path_parts) > 2 else None
            resource_id: int | None = None
            if len(path_parts) > 3:
                try:
                    resource_id = int(path_parts[3])
                except ValueError:
                    pass

            action = f"{resource}.{request.method.lower()}" if resource else request.method.lower()
            ip = request.client.host if request.client else None

            factory = get_session_factory()
            async with factory() as session:
                log = AuditLog(
                    user_id=user_id,
                    actor=actor,
                    action=action,
                    resource=resource,
                    resource_id=resource_id,
                    ip_address=ip,
                    occurred_at=datetime.now(timezone.utc),
                )
                session.add(log)
                await session.commit()
        except Exception as exc:
            logger.warning("Audit log failed: %s", exc)

        return response
