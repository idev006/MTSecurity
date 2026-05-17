"""Permission matrix for the 6-actor model."""

from __future__ import annotations

from enum import StrEnum

from fastapi import HTTPException, status


class Role(StrEnum):
    SYSTEM = "SYSTEM"
    SUPERADMIN = "SUPERADMIN"
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    AUDITOR = "AUDITOR"
    EXTERNAL_SYSTEM = "EXTERNAL_SYSTEM"


# Permission → minimum role required (checked hierarchically)
_ROLE_HIERARCHY: dict[str, int] = {
    Role.SYSTEM:          0,
    Role.SUPERADMIN:      1,
    Role.ADMIN:           2,
    Role.OPERATOR:        3,
    Role.AUDITOR:         4,
    Role.EXTERNAL_SYSTEM: 5,
}

# Explicit permission table: permission_name → set of allowed roles
_PERMISSIONS: dict[str, set[str]] = {
    # User management
    "users:create":         {Role.SUPERADMIN},
    "users:read":           {Role.SUPERADMIN, Role.ADMIN},
    "users:update":         {Role.SUPERADMIN},
    "users:delete":         {Role.SUPERADMIN},

    # Camera management
    "cameras:create":       {Role.SUPERADMIN, Role.ADMIN},
    "cameras:read":         {Role.SUPERADMIN, Role.ADMIN, Role.OPERATOR, Role.AUDITOR},
    "cameras:update":       {Role.SUPERADMIN, Role.ADMIN},
    "cameras:delete":       {Role.SUPERADMIN},
    "cameras:stream":       {Role.SUPERADMIN, Role.ADMIN, Role.OPERATOR},

    # Zone & Rule management
    "zones:create":         {Role.SUPERADMIN, Role.ADMIN},
    "zones:read":           {Role.SUPERADMIN, Role.ADMIN, Role.OPERATOR, Role.AUDITOR},
    "zones:update":         {Role.SUPERADMIN, Role.ADMIN},
    "zones:delete":         {Role.SUPERADMIN, Role.ADMIN},
    "rules:create":         {Role.SUPERADMIN, Role.ADMIN},
    "rules:read":           {Role.SUPERADMIN, Role.ADMIN, Role.OPERATOR, Role.AUDITOR},
    "rules:update":         {Role.SUPERADMIN, Role.ADMIN},
    "rules:delete":         {Role.SUPERADMIN, Role.ADMIN},

    # Events & Alerts
    "events:read":          {Role.SUPERADMIN, Role.ADMIN, Role.OPERATOR, Role.AUDITOR},
    "events:delete":        {Role.SUPERADMIN, Role.ADMIN},
    "alerts:acknowledge":   {Role.SUPERADMIN, Role.ADMIN, Role.OPERATOR},
    "alerts:silence":       {Role.SUPERADMIN, Role.ADMIN},
    "alerts:escalate":      {Role.SUPERADMIN, Role.ADMIN, Role.OPERATOR},

    # Analytics & Audit
    "analytics:read":       {Role.SUPERADMIN, Role.ADMIN, Role.AUDITOR},
    "audit_log:read":       {Role.SUPERADMIN, Role.AUDITOR},

    # NLQ
    "nlq:query":            {Role.SUPERADMIN, Role.ADMIN, Role.OPERATOR, Role.AUDITOR},
    "nlq:command":          {Role.SUPERADMIN, Role.ADMIN},

    # LPR
    "lpr:read":             {Role.SUPERADMIN, Role.ADMIN, Role.OPERATOR, Role.AUDITOR},
    "lpr:write":            {Role.SUPERADMIN, Role.ADMIN},

    # API Keys
    "api_keys:manage":      {Role.SUPERADMIN, Role.ADMIN},
    "api_keys:external":    {Role.EXTERNAL_SYSTEM},
}


def has_permission(role: str, permission: str) -> bool:
    allowed = _PERMISSIONS.get(permission)
    if allowed is None:
        return False
    return role in allowed


def require_permission(role: str, permission: str) -> None:
    if not has_permission(role, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{role}' does not have permission '{permission}'",
        )


def require_camera_scope(
    camera_id: int,
    allowed_camera_ids: list[int] | None,
) -> None:
    """None means unrestricted (admin/superadmin). List means scoped operator."""
    if allowed_camera_ids is None:
        return
    if camera_id not in allowed_camera_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access to camera {camera_id} not permitted for your account",
        )
