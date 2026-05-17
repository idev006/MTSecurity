"""Auth router — login, logout, refresh, me."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select

from api.deps import CurrentUser, DBDep
from auth.jwt_handler import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    is_blacklisted,
    purge_expired_blacklist,
)
from auth.password import verify_password
from models.system_setting import SystemSetting
from models.user import User
from schemas.user import LoginRequest, TokenResponse, UserRead


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


async def _get_setting_int(key: str, default: int, db) -> int:
    """Read an integer setting from system_settings, falling back to default."""
    row = await db.get(SystemSetting, key)
    if row is not None:
        try:
            return int(row.value)
        except ValueError:
            pass
    return default

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: DBDep) -> TokenResponse:
    cfg = request.app.state.cfg

    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    access_minutes = await _get_setting_int(
        "jwt_access_token_expire_minutes", cfg.jwt_access_token_expire_minutes, db)
    refresh_days = await _get_setting_int(
        "jwt_refresh_token_expire_days", cfg.jwt_refresh_token_expire_days, db)

    access = create_access_token(
        subject=user.username,
        role=user.role,
        secret=cfg.jwt_secret_key.get_secret_value(),
        algorithm=cfg.jwt_algorithm,
        expires_minutes=access_minutes,
    )
    refresh = create_refresh_token(
        subject=user.username,
        secret=cfg.jwt_secret_key.get_secret_value(),
        algorithm=cfg.jwt_algorithm,
        expires_days=refresh_days,
    )
    await purge_expired_blacklist(db)
    await db.commit()

    logger.info("Login: user=%s role=%s access=%dm refresh=%dd",
                user.username, user.role, access_minutes, refresh_days)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=access_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest, user: CurrentUser, request: Request, db: DBDep) -> None:
    cfg = request.app.state.cfg
    secret = cfg.jwt_secret_key.get_secret_value()

    # Blacklist access token (from Authorization header)
    auth_header = request.headers.get("authorization", "")
    access_token = auth_header.removeprefix("Bearer ").strip()
    try:
        payload = decode_token(access_token, secret, cfg.jwt_algorithm)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        await blacklist_token(payload["jti"], exp, db)
    except Exception:
        pass  # Already expired or invalid

    # Blacklist refresh token (from request body) — fixes BUG-015 partial logout
    if body.refresh_token:
        try:
            rp = decode_token(body.refresh_token, secret, cfg.jwt_algorithm)
            if rp.get("type") == "refresh":
                rexp = datetime.fromtimestamp(rp["exp"], tz=timezone.utc)
                await blacklist_token(rp["jti"], rexp, db)
        except Exception:
            pass  # Already expired or invalid

    await db.commit()
    logger.info("Logout: user=%s", user.username)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: dict, request: Request, db: DBDep) -> TokenResponse:
    cfg = request.app.state.cfg
    token = body.get("refresh_token", "")
    try:
        payload = decode_token(token, cfg.jwt_secret_key.get_secret_value(), cfg.jwt_algorithm)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong token type")

    jti = payload.get("jti", "")
    if await is_blacklisted(jti, db):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token revoked")

    username: str = payload["sub"]
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found")

    # Rotate: blacklist old refresh token
    exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
    await blacklist_token(jti, exp, db)

    access_minutes = await _get_setting_int(
        "jwt_access_token_expire_minutes", cfg.jwt_access_token_expire_minutes, db)
    refresh_days = await _get_setting_int(
        "jwt_refresh_token_expire_days", cfg.jwt_refresh_token_expire_days, db)

    access = create_access_token(
        subject=user.username, role=user.role,
        secret=cfg.jwt_secret_key.get_secret_value(),
        algorithm=cfg.jwt_algorithm,
        expires_minutes=access_minutes,
    )
    new_refresh = create_refresh_token(
        subject=user.username,
        secret=cfg.jwt_secret_key.get_secret_value(),
        algorithm=cfg.jwt_algorithm,
        expires_days=refresh_days,
    )
    await db.commit()

    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=access_minutes * 60,
    )


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> User:
    return user
