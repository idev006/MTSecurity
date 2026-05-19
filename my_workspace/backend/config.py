"""Application settings — loaded once from environment / .env file."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "MTSecurity"
    app_version: str = "2.0.0"
    debug: bool = False
    environment: str = "production"   # "development" | "production" | "test"

    # ── Server ───────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # ── Database ─────────────────────────────────────────────────────────────
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/mtsecurity.db",
        description="Async SQLAlchemy URL. Use postgresql+asyncpg://... for production.",
    )

    # ── Security ─────────────────────────────────────────────────────────────
    jwt_secret_key: SecretStr = Field(..., description="Min 32 random bytes — set in .env")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # AES-256 key for RTSP URL encryption (base64-encoded Fernet key)
    encryption_key: SecretStr = Field(..., description="Fernet key — generate with Fernet.generate_key()")

    # ── AI ───────────────────────────────────────────────────────────────────
    model_path: Path = BASE_DIR / "data" / "models" / "yolo11n.xml"
    model_device: str = "CPU"          # "CPU" | "GPU" | "AUTO"
    ai_confidence_threshold: float = 0.6
    ai_target_classes: list[int] | None = None  # None = all COCO classes; e.g. [0,15,16] = person+cat+dog
    ai_queue_max_wip: int = 2          # max concurrent AI inferences

    # ── Streaming ────────────────────────────────────────────────────────────
    stream_thumbnail_fps: int = 3
    stream_monitor_fps: int = 10

    # ── Notifications ────────────────────────────────────────────────────────
    line_channel_access_token: SecretStr | None = None
    line_channel_id: str | None = None
    discord_webhook_url: SecretStr | None = None
    slack_webhook_url: SecretStr | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: SecretStr | None = None
    smtp_from: str | None = None

    # ── NLQ ──────────────────────────────────────────────────────────────────
    anthropic_api_key: SecretStr | None = None
    nlq_enabled: bool = False
    nlq_max_results: int = 50
    nlq_rate_limit_per_minute: int = 20

    # ── Storage ──────────────────────────────────────────────────────────────
    snapshot_dir: Path = BASE_DIR / "data" / "snapshots"
    clip_dir: Path = BASE_DIR / "data" / "clips"
    max_snapshot_age_days: int = 30
    disk_alert_threshold_gb: float = 20.0

    # ── Annotation ───────────────────────────────────────────────────────────
    # Override the auto-scaled font size on snapshot bounding-box labels.
    # 0.0 = auto (scales with image resolution — recommended).
    # Set a positive value (e.g. 0.6) to force a fixed scale at all resolutions.
    annotation_font_scale: float = 0.0
    # Override the bounding-box border thickness (px).
    # 0 = auto.  Set e.g. 2 for a fixed 2 px border.
    annotation_box_thickness: int = 0

    # ── FFmpeg ────────────────────────────────────────────────────────────────
    # Absolute path to the ffmpeg executable.
    # Leave empty ("") to search PATH automatically.
    ffmpeg_path: str = ""
    # Output resolution for saved clips.
    # clip_height=480, clip_width=854 → 854×480 (16:9 landscape, YouTube-friendly).
    # Set both to 0 to keep the original camera resolution.
    clip_height: int = 480
    clip_width: int = 854

    # ── URLs ─────────────────────────────────────────────────────────────────
    # Public-facing base URL — used for building snapshot/clip links in alerts
    base_url: str = "http://localhost:8000"
    # Comma-separated allowed CORS origins (debug mode adds these automatically)
    cors_origins: str = ""

    # ── Rate limiting ────────────────────────────────────────────────────────
    rate_limit_login: str = "5/minute"
    rate_limit_api: str = "200/minute"

    @field_validator("jwt_secret_key", mode="before")
    @classmethod
    def validate_jwt_secret(cls, v: str | SecretStr) -> SecretStr:
        raw = v.get_secret_value() if isinstance(v, SecretStr) else str(v)
        if len(raw) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return SecretStr(raw)

    def ensure_dirs(self) -> None:
        self.snapshot_dir.mkdir(parents=True, exist_ok=True)
        self.clip_dir.mkdir(parents=True, exist_ok=True)
        (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
