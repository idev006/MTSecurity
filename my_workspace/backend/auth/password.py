"""Password hashing and verification using bcrypt."""

from __future__ import annotations

import re

import bcrypt


_ROUNDS = 12
_MIN_LENGTH = 8
_POLICY_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")


def hash_password(plain: str) -> str:
    if len(plain) < _MIN_LENGTH:
        raise ValueError(f"Password must be at least {_MIN_LENGTH} characters")
    salt = bcrypt.gensalt(rounds=_ROUNDS)
    return bcrypt.hashpw(plain.encode(), salt).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def validate_policy(plain: str) -> list[str]:
    """Returns list of policy violations; empty list means password is valid."""
    errors: list[str] = []
    if len(plain) < _MIN_LENGTH:
        errors.append(f"At least {_MIN_LENGTH} characters required")
    if not re.search(r"[a-z]", plain):
        errors.append("At least one lowercase letter required")
    if not re.search(r"[A-Z]", plain):
        errors.append("At least one uppercase letter required")
    if not re.search(r"\d", plain):
        errors.append("At least one digit required")
    return errors
