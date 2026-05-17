"""Export all ORM models so Base.metadata sees every table."""

from models.alert_note import AlertNote
from models.api_key import APIKey
from models.audit_log import AuditLog
from models.base import Base, TimestampMixin
from models.camera import Camera
from models.event import Event
from models.lpr_whitelist import LPRWhitelist
from models.notification import Notification
from models.rule import Rule
from models.system_setting import SystemSetting
from models.token_blacklist import TokenBlacklist
from models.user import User
from models.zone import Zone

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "Camera",
    "Zone",
    "Rule",
    "Event",
    "Notification",
    "LPRWhitelist",
    "APIKey",
    "AuditLog",
    "AlertNote",
    "TokenBlacklist",
    "SystemSetting",
]
