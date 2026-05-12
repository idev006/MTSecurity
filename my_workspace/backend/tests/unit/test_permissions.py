"""Phase 1 Gate — Unit tests for auth/permissions.py."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from auth.permissions import Role, has_permission, require_camera_scope, require_permission


# ── has_permission ────────────────────────────────────────────────────────────

def test_superadmin_can_create_users():
    assert has_permission(Role.SUPERADMIN, "users:create") is True


def test_operator_cannot_create_users():
    assert has_permission(Role.OPERATOR, "users:create") is False


def test_auditor_can_read_events():
    assert has_permission(Role.AUDITOR, "events:read") is True


def test_auditor_cannot_acknowledge_alerts():
    assert has_permission(Role.AUDITOR, "alerts:acknowledge") is False


def test_operator_can_acknowledge_alerts():
    assert has_permission(Role.OPERATOR, "alerts:acknowledge") is True


def test_admin_can_update_zones():
    assert has_permission(Role.ADMIN, "zones:update") is True


def test_external_system_cannot_stream():
    assert has_permission(Role.EXTERNAL_SYSTEM, "cameras:stream") is False


def test_unknown_permission_returns_false():
    assert has_permission(Role.SUPERADMIN, "nonexistent:action") is False


# ── require_permission ────────────────────────────────────────────────────────

def test_require_permission_passes_for_allowed_role():
    require_permission(Role.ADMIN, "cameras:create")   # should not raise


def test_require_permission_raises_403_for_disallowed_role():
    with pytest.raises(HTTPException) as exc_info:
        require_permission(Role.OPERATOR, "users:delete")
    assert exc_info.value.status_code == 403


# ── require_camera_scope ──────────────────────────────────────────────────────

def test_unrestricted_scope_allows_any_camera():
    require_camera_scope(99, None)   # None = unrestricted, should not raise


def test_scoped_operator_allowed_camera():
    require_camera_scope(3, [1, 2, 3])   # should not raise


def test_scoped_operator_denied_camera():
    with pytest.raises(HTTPException) as exc_info:
        require_camera_scope(5, [1, 2, 3])
    assert exc_info.value.status_code == 403
