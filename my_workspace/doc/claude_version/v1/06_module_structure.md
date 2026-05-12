# 06 — Module Structure

> เอกสารนี้แสดงโครงสร้าง Codebase ที่ควรจะเป็น
> พร้อม interface contract ของแต่ละ module หลัก
> เขียนโค้ดตัวอย่างให้เห็นภาพ ไม่ใช่ implementation จริง

---

## 1. โครงสร้างไดเรกทอรี

```
mtsecurity/
│
├── main.py                          # Entry point — เริ่ม orchestrator
├── config.py                        # Settings จาก .env / env vars
├── pyproject.toml
├── docker-compose.yml
├── .env.example
│
├── ingestion/                       # Layer A: รับข้อมูลจากกล้อง
│   ├── __init__.py
│   ├── camera_manager.py            # จัดการ thread pool ของกล้อง
│   ├── camera_thread.py             # 1 thread ต่อ 1 กล้อง
│   ├── frame_buffer.py              # deque buffer ต่อ camera_id
│   └── onvif_scanner.py             # ค้นหากล้อง ONVIF อัตโนมัติ
│
├── ai/                              # Layer B: AI Processing
│   ├── __init__.py
│   ├── pipeline.py                  # AI main loop (round-robin)
│   ├── inference_engine.py          # OpenVINO wrapper
│   ├── model_registry.py            # โหลด/จัดการหลาย model
│   ├── detector.py                  # YOLOv8 postprocess
│   ├── tracker.py                   # ByteTrack wrapper
│   ├── lpr/
│   │   ├── plate_detector.py        # detect plate bbox
│   │   └── ocr_engine.py            # PaddleOCR wrapper
│   └── fire_detector.py             # specialized model
│
├── rules/                           # Layer C: Business Logic
│   ├── __init__.py
│   ├── rule_engine.py               # orchestrate rule evaluation
│   ├── zone_manager.py              # Zone CRUD + in-memory cache
│   ├── schedule_manager.py          # time-based activation
│   ├── dwell_tracker.py             # สะสม dwell_time ต่อ (track, zone)
│   └── behaviors/
│       ├── intrusion.py
│       ├── loitering.py
│       ├── line_crossing.py
│       ├── crowd_density.py
│       └── abandoned_object.py
│
├── alerts/                          # Alert pipeline
│   ├── __init__.py
│   ├── alert_manager.py             # debounce + cooldown (Redis)
│   ├── snapshot.py                  # annotate + save JPEG
│   ├── clip_recorder.py             # บันทึก video clip รอบ event
│   └── notifications/
│       ├── base.py                  # NotificationChannel ABC
│       ├── line_notify.py
│       ├── email_sender.py
│       ├── webhook_sender.py
│       └── mqtt_publisher.py
│
├── api/                             # Layer D: FastAPI
│   ├── __init__.py
│   ├── app.py                       # FastAPI app factory
│   ├── deps.py                      # Depends: db, current_user
│   ├── routers/
│   │   ├── cameras.py               # CRUD /api/cameras/
│   │   ├── zones.py                 # CRUD /api/zones/
│   │   ├── rules.py                 # CRUD /api/rules/
│   │   ├── events.py                # GET /api/events/ + filters
│   │   ├── lpr.py                   # CRUD /api/lpr/whitelist/
│   │   └── analytics.py             # GET /api/analytics/
│   └── websocket/
│       ├── hub.py                   # WebSocket connection manager
│       ├── stream_handler.py        # /ws/stream/{camera_id}
│       └── alert_handler.py         # /ws/alerts
│
├── models/                          # SQLAlchemy ORM Models (DB-agnostic)
│   ├── __init__.py                  # export ทุก model จากที่นี่
│   ├── base.py                      # DeclarativeBase, utcnow()
│   ├── camera.py
│   ├── zone.py
│   ├── rule.py
│   ├── event.py
│   ├── notification.py
│   └── lpr_whitelist.py
│
├── db/                              # Database session & lifecycle
│   ├── __init__.py
│   ├── session.py                   # engine + AsyncSessionLocal + get_db()
│   ├── init_db.py                   # create_all() สำหรับ development
│   └── pragmas.py                   # SQLite PRAGMA setup (WAL, FK, timeout)
│
├── schemas/                         # Pydantic v2 Schemas (API I/O)
│   ├── camera.py
│   ├── zone.py
│   ├── rule.py
│   ├── event.py
│   └── alert.py
│
├── analytics/
│   ├── heatmap.py                   # สร้าง heatmap PNG
│   ├── statistics.py                # aggregation queries
│   └── report.py                    # PDF/CSV export
│
├── migrations/                      # Alembic (track schema changes)
│   ├── env.py
│   └── versions/
│
├── data/                            # runtime data (gitignored)
│   ├── mtsecurity.db                # SQLite database file
│   ├── snapshots/
│   └── clips/
│
└── tests/
    ├── conftest.py                  # fixtures: test db (SQLite :memory:)
    ├── unit/
    │   ├── test_rule_engine.py
    │   ├── test_dwell_tracker.py
    │   └── test_line_crossing.py
    └── integration/
        ├── test_alert_flow.py
        └── test_api_events.py
```

---

## 2. Interface Contracts หลัก

### 2.1 FrameBuffer

```python
# ingestion/frame_buffer.py
from collections import deque
from dataclasses import dataclass
import numpy as np
import threading

@dataclass
class Frame:
    camera_id:   int
    pixels:      np.ndarray    # H×W×3 uint8
    captured_at: float         # unix timestamp
    seq:         int

class FrameBuffer:
    """Thread-safe, per-camera circular buffer (maxlen=1)."""

    def __init__(self):
        self._buffers: dict[int, deque[Frame]] = {}
        self._lock = threading.Lock()

    def register(self, camera_id: int) -> None:
        with self._lock:
            self._buffers[camera_id] = deque(maxlen=1)

    def put(self, frame: Frame) -> None:
        with self._lock:
            self._buffers[frame.camera_id].append(frame)

    def get_latest(self, camera_id: int) -> Frame | None:
        with self._lock:
            buf = self._buffers.get(camera_id)
            return buf[-1] if buf else None

    def get_all_latest(self) -> dict[int, Frame]:
        with self._lock:
            return {
                cid: buf[-1]
                for cid, buf in self._buffers.items()
                if buf
            }
```

### 2.2 InferenceEngine

```python
# ai/inference_engine.py
from openvino.runtime import Core, CompiledModel
import numpy as np
from dataclasses import dataclass

@dataclass
class Detection:
    class_id:   int
    class_name: str
    confidence: float
    x1: float; y1: float; x2: float; y2: float

class InferenceEngine:
    """Single-model, CPU OpenVINO inference engine."""

    def __init__(self, model_path: str, device: str = "CPU"):
        core = Core()
        model = core.read_model(model_path)
        self._net = core.compile_model(model, device)
        self._input_layer = self._net.input(0)

    def infer(self, frame: np.ndarray) -> list[Detection]:
        """
        frame: BGR uint8 H×W×3
        returns: list of Detections in pixel coordinates
        """
        blob = self._preprocess(frame)
        result = self._net(blob)[self._net.output(0)]
        return self._postprocess(result, frame.shape)

    def _preprocess(self, frame: np.ndarray) -> np.ndarray: ...
    def _postprocess(self, output, original_shape) -> list[Detection]: ...
```

### 2.3 RuleEngine

```python
# rules/rule_engine.py
from dataclasses import dataclass
from enum import Enum

class EventType(str, Enum):
    INTRUSION        = "intrusion"
    LOITERING        = "loitering"
    LINE_CROSSING    = "line_crossing"
    CROWD_DENSITY    = "crowd_density"
    ABANDONED_OBJECT = "abandoned_object"

@dataclass
class RuleEvent:
    event_type:  EventType
    camera_id:   int
    zone_id:     int
    rule_id:     int
    track_id:    int
    object_class: str
    confidence:  float
    bbox:        tuple[float,float,float,float]
    timestamp:   float
    extra:       dict

class RuleEngine:
    """
    Evaluates active rules against a list of tracked objects.
    Stateless per call — dwell_time state lives in DwellTracker.
    """

    def __init__(self, zone_manager, dwell_tracker, schedule_manager):
        self._zones   = zone_manager
        self._dwell   = dwell_tracker
        self._sched   = schedule_manager

    def evaluate(
        self,
        camera_id: int,
        tracks: list,         # list[TrackedObject]
        frame_timestamp: float,
        dt: float,            # seconds since last frame
    ) -> list[RuleEvent]:
        """
        Returns zero or more RuleEvents.
        Caller (AlertManager) decides which to suppress.
        """
        events = []
        active_rules = self._zones.get_active_rules(camera_id)

        for rule in active_rules:
            if not self._sched.is_active(rule):
                continue
            zone = self._zones.get_zone(rule.zone_id)
            for track in tracks:
                if track.class_name not in rule.target_classes:
                    continue
                ev = self._dispatch(rule, zone, track, dt, frame_timestamp)
                if ev:
                    events.append(ev)
        return events

    def _dispatch(self, rule, zone, track, dt, ts) -> RuleEvent | None:
        match rule.rule_type:
            case "intrusion":        return self._check_intrusion(rule, zone, track, ts)
            case "loitering":        return self._check_loitering(rule, zone, track, dt, ts)
            case "line_crossing":    return self._check_line_crossing(rule, zone, track, ts)
            case "crowd_density":    return None  # evaluated separately per zone
            case "abandoned_object": return self._check_abandoned(rule, zone, track, ts)
            case _:                  return None
```

### 2.4 AlertManager

```python
# alerts/alert_manager.py
import asyncio
import redis.asyncio as aioredis

class AlertManager:
    """
    Filters Events by cooldown, then dispatches to:
      - SnapshotService (save JPEG)
      - Database (INSERT event)
      - NotificationService (LINE/Email/Webhook/MQTT)
      - WebSocket Hub (real-time push)
    """

    def __init__(
        self,
        redis_client: aioredis.Redis,
        snapshot_svc,
        notification_svc,
        db_session_factory,
        ws_hub,
    ):
        self._redis = redis_client
        self._snap  = snapshot_svc
        self._notif = notification_svc
        self._db    = db_session_factory
        self._ws    = ws_hub

    async def process(self, event: "RuleEvent", frame: "Frame") -> bool:
        """Returns True if alert was fired, False if suppressed."""
        key = f"cd:{event.camera_id}:{event.zone_id}:{event.track_id}:{event.event_type}"

        if await self._redis.exists(key):
            await self._log_suppressed(event)
            return False

        snapshot_path = await self._snap.save(frame, event)
        async with self._db() as session:
            db_event = await self._insert_event(session, event, snapshot_path)

        await self._notif.dispatch_all(db_event, snapshot_path)
        await self._redis.setex(key, event.cooldown_sec, "1")
        await self._ws.broadcast_alert(db_event)
        return True
```

### 2.5 NotificationChannel ABC

```python
# alerts/notifications/base.py
from abc import ABC, abstractmethod

class NotificationChannel(ABC):
    """
    ทุก channel ต้อง implement send()
    ถ้า send ล้มเหลว ต้อง raise exception
    AlertManager จะ retry หรือ log ตามนโยบาย
    """

    @abstractmethod
    async def send(self, payload: "AlertPayload", image_path: str | None) -> None: ...

    @property
    @abstractmethod
    def channel_name(self) -> str: ...
```

---

## 3. main.py — Service Orchestration

```python
# main.py
import asyncio
import threading
from config import Settings
from ingestion import CameraManager, FrameBuffer
from ai import AIPipeline
from rules import RuleEngine, ZoneManager, DwellTracker, ScheduleManager
from alerts import AlertManager, SnapshotService, NotificationService
from api import create_app

async def main():
    settings = Settings()

    # ─── Shared state ─────────────────────────────────────
    buffer        = FrameBuffer()
    zone_manager  = ZoneManager(db_url=settings.db_url)
    dwell_tracker = DwellTracker()
    sched_manager = ScheduleManager()

    # ─── Layer A: Ingestion (threads) ─────────────────────
    cam_manager = CameraManager(buffer, db_url=settings.db_url)
    await cam_manager.start_all()          # spawn 1 thread per camera

    # ─── Layer B+C: AI + Rule (single thread loop) ────────
    rule_engine = RuleEngine(zone_manager, dwell_tracker, sched_manager)
    alert_mgr   = AlertManager(...)
    ai_pipeline = AIPipeline(
        buffer=buffer,
        rule_engine=rule_engine,
        alert_manager=alert_mgr,
        settings=settings,
    )
    ai_thread = threading.Thread(target=ai_pipeline.run, daemon=True)
    ai_thread.start()

    # ─── Layer D: API (async) ─────────────────────────────
    app = create_app(settings, zone_manager)
    import uvicorn
    config = uvicorn.Config(app, host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 4. Configuration (config.py)

```python
# config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Database ──────────────────────────────────────────────────
    # Phase 1 (SQLite):     sqlite+aiosqlite:///./data/mtsecurity.db
    # Phase 2 (PostgreSQL): postgresql+asyncpg://user:pass@host/db
    database_url: str = "sqlite+aiosqlite:///./data/mtsecurity.db"
    db_echo:      bool = False   # True = log SQL queries (dev only)

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    # ── Cache ──────────────────────────────────────────────────────
    # Phase 1: ถ้าไม่มี Redis ให้ตั้ง redis_url="" → ใช้ TTLCache แทน
    redis_url:    str = ""       # "" = ใช้ in-memory TTLCache (dev)

    @property
    def use_redis(self) -> bool:
        return bool(self.redis_url)

    # ── AI ────────────────────────────────────────────────────────
    model_path:      str   = "./data/models/yolov8n_openvino_int8"
    device:          str   = "CPU"      # CPU | GPU | AUTO
    input_size:      int   = 640        # 320 หรือ 640
    conf_threshold:  float = 0.45
    iou_threshold:   float = 0.45

    # ── Ingestion ─────────────────────────────────────────────────
    max_cameras:       int = 10
    frame_buffer_size: int = 1         # maxlen ของ deque ต่อกล้อง

    # ── Notifications ─────────────────────────────────────────────
    line_channel_token: str = ""
    smtp_host:          str = "smtp.gmail.com"
    smtp_port:          int = 587
    smtp_user:          str = ""
    smtp_password:      str = ""
    webhook_url:        str = ""
    mqtt_broker:        str = "localhost"
    mqtt_port:          int = 1883

    # ── Storage ───────────────────────────────────────────────────
    snapshot_dir:             str = "./data/snapshots"
    clip_dir:                 str = "./data/clips"
    retention_days_snapshots: int = 90
    retention_days_clips:     int = 30
```

### .env.example

```bash
# .env.example — copy เป็น .env แล้วแก้ค่า

# ── Database (Phase 1: SQLite) ──────────────────────────────────
DATABASE_URL=sqlite+aiosqlite:///./data/mtsecurity.db
DB_ECHO=false

# ── Database (Phase 2: PostgreSQL) — uncomment เมื่อพร้อม migrate
# DATABASE_URL=postgresql+asyncpg://mtsec:password@localhost:5432/mtsecurity

# ── Cache ────────────────────────────────────────────────────────
# เว้นว่าง = ใช้ in-memory cache (Phase 1)
REDIS_URL=
# REDIS_URL=redis://localhost:6379/0   ← เปิดเมื่อมี Redis

# ── AI ──────────────────────────────────────────────────────────
MODEL_PATH=./data/models/yolov8n_openvino_int8
DEVICE=CPU
INPUT_SIZE=640
CONF_THRESHOLD=0.45

# ── Notifications ────────────────────────────────────────────────
LINE_CHANNEL_TOKEN=your_line_channel_token_here
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_app_password
WEBHOOK_URL=https://your-webhook.example.com/alert

# ── Storage ──────────────────────────────────────────────────────
SNAPSHOT_DIR=./data/snapshots
CLIP_DIR=./data/clips
```

---

## 5. Testing Strategy

```
Unit Tests (ไม่ต้องการ DB หรือกล้อง):
  ├── test_rule_engine.py       — mock Track + Zone, ตรวจ Event output
  ├── test_dwell_tracker.py     — simulate เวลา, ตรวจ dwell accumulation
  ├── test_line_crossing.py     — vectors ต่างๆ ที่ cross/ไม่ cross
  ├── test_frame_buffer.py      — concurrent put/get, maxlen=1 behavior
  └── test_alert_manager.py     — mock Redis, ตรวจ cooldown logic

Integration Tests (ใช้ SQLite :memory: — ไม่ต้องการ Docker):
  ├── test_alert_flow.py        — end-to-end: Event → DB → Notification
  ├── test_api_events.py        — HTTP calls, filter params, pagination
  └── test_zone_crud.py         — create zone → rule engine picks it up

  conftest.py fixture:
    @pytest.fixture
    async def db():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with AsyncSession(engine) as session:
            yield session

Performance Tests (manual + monitoring):
  └── bench_inference.py        — วัด ms/frame บน target hardware
```

---

## 6. สรุป Dependency Flow (ห้ามวน)

```
config
  └─ ingestion (FrameBuffer, CameraManager)
       └─ ai (AIPipeline, InferenceEngine, Tracker)
            └─ rules (RuleEngine, ZoneManager, DwellTracker)
                 └─ alerts (AlertManager, NotificationService)
                      └─ api (FastAPI, WebSocket)
                           └─ models (SQLAlchemy)

ทิศทางเดียว — Layer บนไม่รู้จัก Layer ล่าง
ZoneManager ส่งข้อมูลไป RuleEngine ผ่าน method call
AlertManager ส่งไป WebSocket Hub ผ่าน event queue
ไม่มี circular import
```
