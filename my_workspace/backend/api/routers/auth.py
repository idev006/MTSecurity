"""Auth router — login, logout, refresh, me."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, HTTPException, Request, status
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
from models.user import User
from schemas.user import LoginRequest, TokenResponse, UserRead

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request, db: DBDep) -> TokenResponse:
    cfg = request.app.state.cfg

    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    access = create_access_token(
        subject=user.username,
        role=user.role,
        secret=cfg.jwt_secret_key.get_secret_value(),
        algorithm=cfg.jwt_algorithm,
        expires_minutes=cfg.jwt_access_token_expire_minutes,
    )
    refresh = create_refresh_token(
        subject=user.username,
        secret=cfg.jwt_secret_key.get_secret_value(),
        algorithm=cfg.jwt_algorithm,
        expires_days=cfg.jwt_refresh_token_expire_days,
    )
    await purge_expired_blacklist(db)
    await db.commit()

    logger.info("Login: user=%s role=%s", user.username, user.role)
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        token_type="bearer",
        expires_in=cfg.jwt_access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(user: CurrentUser, request: Request, db: DBDep) -> None:
    # Extract JTI from the Authorization header
    auth = request.headers.get("authorization", "")
    token = auth.removeprefix("Bearer ").strip()
    cfg = request.app.state.cfg
    try:
        payload = decode_token(token, cfg.jwt_secret_key.get_secret_value(), cfg.jwt_algorithm)
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        await blacklist_token(payload["jti"], exp, db)
        await db.commit()
    except Exception:
        pass  # Already expired or invalid — treat as logged out


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

    access = create_access_token(
        subject=user.username, role=user.role,
        secret=cfg.jwt_secret_key.get_secret_value(),
        algorithm=cfg.jwt_algorithm,
        expires_minutes=cfg.jwt_access_token_expire_minutes,
    )
    new_refresh = create_refresh_token(
        subject=user.username,
        secret=cfg.jwt_secret_key.get_secret_value(),
        algorithm=cfg.jwt_algorithm,
        expires_days=cfg.jwt_refresh_token_expire_days,
    )
    await db.commit()

    return TokenResponse(
        access_token=access,
        refresh_token=new_refresh,
        token_type="bearer",
        expires_in=cfg.jwt_access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> User:
    return user
