"""Phase 1 Gate — Unit tests for JWT and password modules."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest

from auth.jwt_handler import create_access_token, create_refresh_token, decode_token
from auth.password import hash_password, validate_policy, verify_password


# ── Password ──────────────────────────────────────────────────────────────────

def test_hash_and_verify_valid_password():
    plain = "Secure123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed) is True


def test_wrong_password_fails_verify():
    hashed = hash_password("Correct123")
    assert verify_password("Wrong123", hashed) is False


def test_short_password_raises():
    with pytest.raises(ValueError):
        hash_password("abc")


def test_policy_valid_password():
    assert validate_policy("Secure123") == []


def test_policy_missing_uppercase():
    errors = validate_policy("secure123")
    assert any("uppercase" in e.lower() for e in errors)


def test_policy_missing_digit():
    errors = validate_policy("SecurePass")
    assert any("digit" in e.lower() for e in errors)


# ── JWT ───────────────────────────────────────────────────────────────────────

_SECRET = "a" * 32
_ALGORITHM = "HS256"


def test_create_and_decode_access_token():
    token = create_access_token("alice", "ADMIN", _SECRET, _ALGORITHM, expires_minutes=60)
    payload = decode_token(token, _SECRET, _ALGORITHM)
    assert payload["sub"] == "alice"
    assert payload["role"] == "ADMIN"
    assert payload["type"] == "access"
    assert "jti" in payload


def test_create_and_decode_refresh_token():
    token = create_refresh_token("alice", _SECRET, _ALGORITHM, expires_days=7)
    payload = decode_token(token, _SECRET, _ALGORITHM)
    assert payload["sub"] == "alice"
    assert payload["type"] == "refresh"


def test_expired_token_raises():
    token = create_access_token("alice", "ADMIN", _SECRET, _ALGORITHM, expires_minutes=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token, _SECRET, _ALGORITHM)


def test_wrong_secret_raises():
    token = create_access_token("alice", "ADMIN", _SECRET, _ALGORITHM)
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(token, "wrong_secret" * 4, _ALGORITHM)
