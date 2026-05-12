# 08 — Security Guide
### Secrets Management · TLS · Authentication Flows · Input Validation · Hardening

---

## 1. ภาพรวม Security Model

```
MTSecurity มีพื้นที่เสี่ยงหลัก 4 จุด:

  [1] External Client → API Core        (HTTPS, JWT)
  [2] API Core → Camera (RTSP)          (Credential leak)
  [3] API Core → Notification Services  (Token leak)
  [4] Internal Components ↔ Bus         (Trust boundary)

กฎเหล็ก:
  - Secrets ห้ามอยู่ใน code หรือ git
  - ทุก external connection ต้องใช้ TLS
  - ทุก API endpoint ต้องผ่าน authentication ยกเว้น /api/health
  - ทุก write operation ต้องมี audit record
```

---

## 2. Secrets Management

### 2.1 ประเภท Secret และที่เก็บ

```
Secret                    Dev Environment      Production
─────────────────────────────────────────────────────────────
LINE Channel Access Token  .env (gitignored)   OS env var / Vault
SMTP Password              .env                OS env var / Vault
JWT Secret Key             .env                OS env var / Vault
Database URL               .env                OS env var / Vault
RTSP Credentials           .env / DB encrypted DB encrypted (AES-256)
API Keys (external)        DB (hashed)         DB (hashed)
Redis Password             .env                OS env var / Vault
```

### 2.2 .env Structure (Development Only)

```bash
# .env.example — commit นี้ได้ แต่ห้าม commit .env จริง

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/mtsecurity.db

# Security
JWT_SECRET_KEY=CHANGE_ME_USE_openssl_rand_hex_32
JWT_ALGORITHM=HS256
JWT_ACCESS_EXPIRE_HOURS=8
JWT_REFRESH_EXPIRE_DAYS=30

# AI Model
MODEL_PATH=./data/models/yolo11n.onnx
DEVICE=cpu                           # cpu | gpu

# Notifications
LINE_CHANNEL_ACCESS_TOKEN=           # ห้ามใส่ในไฟล์นี้ที่ commit
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=                       # ห้ามใส่
SMTP_USE_TLS=true

# Storage
SNAPSHOT_DIR=./data/snapshots
CLIP_DIR=./data/clips
SNAPSHOT_RETENTION_DAYS=30

# Redis (optional — ใช้สำหรับ cooldown cache)
REDIS_URL=redis://localhost:6379/0

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false
CORS_ORIGINS=http://localhost:3000   # production: ระบุ domain จริง
```

### 2.3 Production Secrets

```python
# ssot/system_config.py
from pydantic_settings import BaseSettings
from pydantic import SecretStr

class Settings(BaseSettings):
    jwt_secret_key:             SecretStr    # ใช้ SecretStr ป้องกัน logging
    line_channel_access_token:  SecretStr
    smtp_password:              SecretStr
    database_url:               SecretStr

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

# การใช้งาน — ต้องเรียก .get_secret_value() ชัดเจน
token = settings.line_channel_access_token.get_secret_value()
```

### 2.4 RTSP Credential Storage

```python
# RTSP URL มี credential ฝังอยู่: rtsp://user:pass@192.168.1.1/stream
# ห้ามเก็บ plain text ใน DB

# models/camera.py
class Camera(Base):
    rtsp_url_encrypted: Mapped[str] = mapped_column(String(500))
    # เก็บแบบ AES-256-GCM encrypted

# ssot/crypto.py
from cryptography.fernet import Fernet

class CameraCredentialVault:
    def __init__(self, key: bytes):
        self._f = Fernet(key)          # key มาจาก env var VAULT_KEY

    def encrypt(self, rtsp_url: str) -> str:
        return self._f.encrypt(rtsp_url.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        return self._f.decrypt(encrypted.encode()).decode()

# ตอนใช้งาน
vault = CameraCredentialVault(key=os.environ["VAULT_KEY"])
plain_rtsp = vault.decrypt(camera.rtsp_url_encrypted)
cap = cv2.VideoCapture(plain_rtsp)
```

---

## 3. TLS / HTTPS Requirements

### 3.1 Protocol Requirements

```
Connection                Protocol        Required
──────────────────────────────────────────────────────
Client → API REST         HTTPS (TLS 1.2+) ✓ Production
Client → WebSocket        WSS (TLS 1.2+)   ✓ Production
API → LINE Notify         HTTPS            ✓ Always
API → SMTP                STARTTLS/TLS     ✓ Always
API → Webhook             HTTPS            ✓ Always (reject HTTP)
API → Redis               TLS (if remote)  ✓ if Redis not localhost
Camera → API (RTSP)       RTSPS (optional) recommended
```

### 3.2 Development (HTTP allowed)

```python
# api/app.py
def create_app(cfg: Settings) -> FastAPI:
    app = FastAPI(
        title="MTSecurity API",
        docs_url="/docs" if cfg.debug else None,   # Swagger ปิดใน production
        redoc_url=None,
    )

    if not cfg.debug:
        app.add_middleware(HTTPSRedirectMiddleware)  # force HTTPS

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins.split(","),  # ไม่ใช้ ["*"] ใน production
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["Authorization", "Content-Type"],
    )
    return app
```

### 3.3 TLS Certificate (Production)

```bash
# ใช้ Let's Encrypt สำหรับ public server
certbot certonly --standalone -d yourdomain.com

# หรือ self-signed สำหรับ internal network
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem \
  -days 365 -nodes -subj "/CN=mtsecurity.local"

# uvicorn production
uvicorn main:app \
  --host 0.0.0.0 \
  --port 443 \
  --ssl-keyfile ./key.pem \
  --ssl-certfile ./cert.pem
```

---

## 4. Authentication & Token Management

### 4.1 JWT Security Requirements

```python
# auth/jwt_handler.py
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
import secrets

ALGORITHM = "HS256"                    # หรือ RS256 ถ้าต้องการ asymmetric

def create_access_token(payload: dict, secret: str) -> str:
    data = payload.copy()
    data["exp"] = datetime.now(timezone.utc) + timedelta(hours=8)
    data["iat"] = datetime.now(timezone.utc)
    data["jti"] = secrets.token_hex(16)    # JWT ID — สำหรับ revocation
    return jwt.encode(data, secret, algorithm=ALGORITHM)

def create_refresh_token(user_id: int, secret: str) -> str:
    data = {
        "sub":  str(user_id),
        "type": "refresh",
        "exp":  datetime.now(timezone.utc) + timedelta(days=30),
        "jti":  secrets.token_hex(16),
    }
    return jwt.encode(data, secret, algorithm=ALGORITHM)
```

### 4.2 Token Revocation

```python
# auth/token_blacklist.py
# ใช้ Redis เพื่อ blacklist token ที่ถูก logout หรือ expire ก่อนกำหนด

class TokenBlacklist:
    def __init__(self, redis_client):
        self._redis = redis_client

    async def revoke(self, jti: str, expire_at: datetime) -> None:
        ttl = int((expire_at - datetime.now(timezone.utc)).total_seconds())
        if ttl > 0:
            await self._redis.setex(f"blacklist:{jti}", ttl, "1")

    async def is_revoked(self, jti: str) -> bool:
        return await self._redis.exists(f"blacklist:{jti}") > 0

# ใช้ใน auth middleware
async def get_current_actor(token: str, blacklist: TokenBlacklist):
    payload = decode_token(token)
    if await blacklist.is_revoked(payload["jti"]):
        raise HTTPException(status_code=401, detail="Token has been revoked")
    return payload
```

### 4.3 Password Security

```python
# auth/password.py
from passlib.context import CryptContext

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12,          # cost factor — ปรับตาม hardware
)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

# Password Policy (enforce ที่ API layer)
PASSWORD_MIN_LENGTH = 12
PASSWORD_REQUIRE_UPPERCASE = True
PASSWORD_REQUIRE_DIGIT = True
PASSWORD_REQUIRE_SPECIAL = True
```

### 4.4 API Key Security

```python
# API Key สำหรับ External System — ไม่เก็บ plain text ใน DB
import secrets
import hashlib

def generate_api_key() -> tuple[str, str]:
    """Returns (plain_key, hashed_key)"""
    plain = f"mts_{secrets.token_urlsafe(32)}"
    hashed = hashlib.sha256(plain.encode()).hexdigest()
    return plain, hashed

# เก็บแค่ hashed ใน DB
# ส่ง plain กลับให้ user ครั้งเดียวตอนสร้าง — ไม่สามารถดูได้อีก
```

---

## 5. Input Validation & Injection Prevention

### 5.1 RTSP URL Validation

```python
# schemas/camera.py
import re
from pydantic import field_validator

RTSP_PATTERN = re.compile(
    r"^rtsps?://"                          # rtsp:// หรือ rtsps://
    r"([a-zA-Z0-9._%-]+:[^@/]+@)?"        # optional user:pass@
    r"[\w.\-]+"                            # hostname / IP
    r"(:\d{1,5})?"                         # optional port
    r"(/[\w./%\-~]*)?"                     # optional path
    r"$"
)

class CameraCreate(BaseModel):
    rtsp_url: str

    @field_validator("rtsp_url")
    @classmethod
    def validate_rtsp(cls, v: str) -> str:
        if not RTSP_PATTERN.match(v):
            raise ValueError("Invalid RTSP URL format")
        # ป้องกัน SSRF — ห้าม localhost และ internal IP ใน production
        if any(blocked in v for blocked in ["localhost", "127.0.0.1", "0.0.0.0"]):
            raise ValueError("RTSP URL cannot point to localhost")
        return v
```

### 5.2 File Path Traversal Prevention

```python
# alerts/snapshot.py
import os
from pathlib import Path

SNAPSHOT_BASE = Path(settings.snapshot_dir).resolve()

def get_safe_snapshot_path(event_id: int, camera_id: int) -> Path:
    # สร้าง path จาก controlled values เท่านั้น — ไม่รับ user input เป็น path
    filename = f"event_{event_id}_cam{camera_id}.jpg"
    path = (SNAPSHOT_BASE / filename).resolve()

    # ตรวจว่า path ยังอยู่ใน base dir
    if not str(path).startswith(str(SNAPSHOT_BASE)):
        raise ValueError("Path traversal detected")
    return path
```

### 5.3 SQL Injection Prevention

```python
# ใช้ SQLAlchemy ORM เสมอ — ห้าม raw SQL string interpolation
# ✗ อย่าทำ:
await session.execute(f"SELECT * FROM events WHERE camera_id = {camera_id}")

# ✓ ทำแบบนี้:
await session.execute(
    select(Event).where(Event.camera_id == camera_id)
)

# ถ้าจำเป็นต้องใช้ raw SQL — ใช้ parameterized query
await session.execute(
    text("SELECT * FROM events WHERE camera_id = :cid"),
    {"cid": camera_id}
)
```

### 5.4 Zone Coordinates Validation

```python
# schemas/zone.py — เพิ่มจาก 06_domain_model.md
@field_validator("coords")
@classmethod
def validate_coords(cls, v: list) -> list:
    if len(v) < 3:
        raise ValueError("Polygon requires at least 3 points")
    if len(v) > 100:
        raise ValueError("Too many points (max 100)")
    for point in v:
        if len(point) != 2:
            raise ValueError("Each point must be [x, y]")
        x, y = point
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            raise ValueError("Coordinates must be normalized 0.0–1.0")
    return v
```

---

## 6. Rate Limiting

```python
# api/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Limits per endpoint
LOGIN_LIMIT       = "5/minute"     # ป้องกัน brute force
API_GENERAL_LIMIT = "100/minute"   # general endpoints
SNAPSHOT_LIMIT    = "30/minute"    # ป้องกัน snapshot scraping
WEBHOOK_LIMIT     = "200/minute"   # external system

# api/routers/auth.py
@router.post("/login")
@limiter.limit(LOGIN_LIMIT)
async def login(request: Request, credentials: LoginRequest):
    ...
```

---

## 7. Security Headers

```python
# api/middleware/security_headers.py
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"]    = "nosniff"
        response.headers["X-Frame-Options"]            = "DENY"
        response.headers["X-XSS-Protection"]           = "1; mode=block"
        response.headers["Strict-Transport-Security"]  = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"]    = "default-src 'self'"
        response.headers["Referrer-Policy"]            = "strict-origin-when-cross-origin"
        # ลบ header ที่เปิดเผยข้อมูล server
        response.headers.pop("server", None)
        return response
```

---

## 8. Audit Middleware (Auto-logging)

```python
# api/middleware/audit.py
# ทุก mutating request (POST/PUT/DELETE/PATCH) จะถูก log อัตโนมัติ

MUTATING_METHODS = {"POST", "PUT", "DELETE", "PATCH"}

class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if request.method in MUTATING_METHODS:
            actor = getattr(request.state, "actor", None)
            if actor:
                await self._write_audit(
                    actor_id   = actor["sub"],
                    actor_type = actor["actor_type"],
                    action     = f"{request.method} {request.url.path}",
                    ip_address = request.client.host,
                    result     = "success" if response.status_code < 400 else "error",
                )
        return response
```

---

## 9. Security Checklist (Pre-deployment)

```
Authentication
  ☐ JWT secret key ≥ 32 bytes random (openssl rand -hex 32)
  ☐ Refresh token rotation implemented
  ☐ Token blacklist (Redis) working
  ☐ Password bcrypt rounds ≥ 12
  ☐ Login rate limiting active (5/min)

Secrets
  ☐ .env ไม่อยู่ใน git (.gitignore ครอบคลุม)
  ☐ RTSP URL encrypted ใน DB
  ☐ API Keys เก็บแบบ SHA-256 hash เท่านั้น
  ☐ LINE/SMTP credentials ไม่ log ออกมา

Network
  ☐ HTTPS enforced (redirect HTTP → HTTPS)
  ☐ CORS origins ระบุ domain จริง (ไม่ใช่ *)
  ☐ Security headers ครบ
  ☐ Swagger UI ปิดใน production

Input
  ☐ RTSP URL validation + SSRF prevention
  ☐ Snapshot path traversal prevention
  ☐ Zone coords range validation
  ☐ SQL parameterized queries เท่านั้น

Audit
  ☐ ทุก write operation มี audit_log record
  ☐ Login success/failure ถูก log
  ☐ Audit log ไม่สามารถ delete ได้ (append-only)
```
