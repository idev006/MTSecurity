"""JWT token creation, validation, and blacklist management."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.token_blacklist import TokenBlacklist


def create_access_token(
    subject: str,
    role: str,
    secret: str,
    algorithm: str = "HS256",
    expires_minutes: int = 60,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=expires_minutes),
        "type": "access",
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, secret, algorithm=algorithm)


def create_refresh_token(
    subject: str,
    secret: str,
    algorithm: str = "HS256",
    expires_days: int = 7,
) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": subject,
            "jti": str(uuid.uuid4()),
            "iat": now,
            "exp": now + timedelta(days=expires_days),
            "type": "refresh",
        },
        secret,
        algorithm=algorithm,
    )


def decode_token(token: str, secret: str, algorithm: str = "HS256") -> dict[str, Any]:
    """Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure."""
    return jwt.decode(token, secret, algorithms=[algorithm])


async def blacklist_token(jti: str, expires_at: datetime, session: AsyncSession) -> None:
    entry = TokenBlacklist(jti=jti, expires_at=expires_at)
    session.add(entry)
    await session.flush()


async def is_blacklisted(jti: str, session: AsyncSession) -> bool:
    result = await session.execute(
        select(TokenBlacklist).where(TokenBlacklist.jti == jti)
    )
    return result.scalar_one_or_none() is not None


async def purge_expired_blacklist(session: AsyncSession) -> int:
    """Remove expired entries — call periodically (e.g. startup or cron)."""
    now = datetime.now(timezone.utc)
    result = await session.execute(
        delete(TokenBlacklist).where(TokenBlacklist.expires_at < now)
    )
    await session.flush()
    return result.rowcount
