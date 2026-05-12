"""FastAPI dependency injection — DB session, current user, permissions."""

from __future__ import annotations

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth.jwt_handler import decode_token, is_blacklisted
from auth.permissions import require_permission
from db.session import get_db
from models.user import User


_bearer = HTTPBearer(auto_error=False)

# ── DB ────────────────────────────────────────────────────────────────────────

DBDep = Annotated[AsyncSession, Depends(get_db)]


# ── Auth ──────────────────────────────────────────────────────────────────────

async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: DBDep,
) -> User:
    token = credentials.credentials if credentials else request.query_params.get("token")
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    cfg = request.app.state.cfg
    try:
        payload = decode_token(
            token,
            cfg.jwt_secret_key.get_secret_value(),
            cfg.jwt_algorithm,
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong token type")

    jti = payload.get("jti", "")
    if await is_blacklisted(jti, db):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token revoked")

    username: str = payload["sub"]
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ── Permission guards ─────────────────────────────────────────────────────────

def require(permission: str):
    """Factory: returns a Depends that enforces a permission on the current user."""
    async def _check(user: CurrentUser) -> User:
        require_permission(user.role, permission)
        return user
    return Depends(_check)
