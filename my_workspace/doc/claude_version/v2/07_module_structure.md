# 07 — Module Structure (v2 Final)
### Reflects: OSI Layers · API Core · MTP · SSOT · Actors

---

## 1. Directory Tree

```
mtsecurity/
│
├── main.py                          # Orchestrator — boot sequence
├── config.py                        # Pydantic BaseSettings (static)
├── pyproject.toml
├── .env.example
│
│  ════════════════════════════════════════════════
│  PROTOCOL LAYER  (ไม่ขึ้นกับ component ใดๆ)
│  ════════════════════════════════════════════════
├── protocol/
│   ├── mtp.py                       # MTPMessage, MTPMsgType, MTPPriority
│   ├── message_bus.py               # MessageBus (Priority Queue)
│   └── payloads.py                  # Typed payload schemas per MsgType
│
│  ════════════════════════════════════════════════
│  SSOT LAYER  (Single Source of Truth)
│  ════════════════════════════════════════════════
├── ssot/
│   ├── config_service.py            # AuthoritativeConfig (DB-backed, cached)
│   └── state_registry.py           # RuntimeState (in-memory, no persist)
│
│  ════════════════════════════════════════════════
│  L1-L2: PHYSICAL + DATA LINK
│  ════════════════════════════════════════════════
├── ingestion/
│   ├── camera_manager.py            # lifecycle ทุก CameraThread
│   ├── camera_thread.py             # 1 thread/camera → RTSP → FrameBuffer
│   ├── frame_buffer.py              # deque(maxlen=1) per camera_id
│   ├── frame_codec.py               # JPEG encode/decode, resize (L2)
│   └── onvif_scanner.py             # auto-discover ONVIF cameras
│
│  ════════════════════════════════════════════════
│  L3-L5: NETWORK + TRANSPORT + SESSION
│  ════════════════════════════════════════════════
├── ai/
│   ├── pipeline.py                  # AI main loop (round-robin, L3 orchestrate)
│   ├── inference_engine.py          # OpenVINO wrapper (L4 processing)
│   ├── model_registry.py            # load/manage models
│   ├── detector.py                  # YOLOv8 postprocess → Detection
│   ├── tracker.py                   # ByteTrack → Track (L5 session state)
│   ├── session_registry.py          # Track ID ↔ camera mapping
│   ├── lpr/
│   │   ├── plate_detector.py
│   │   └── ocr_engine.py            # PaddleOCR
│   └── fire_detector.py
│
│  ════════════════════════════════════════════════
│  L6-L7: PRESENTATION + APPLICATION
│  ════════════════════════════════════════════════
├── rules/
│   ├── rule_engine.py               # L7 orchestrator — evaluate all rules
│   ├── zone_manager.py              # Zone geometry (reads from SSOT)
│   ├── schedule_manager.py          # time-based rule activation
│   ├── dwell_tracker.py             # dwell_time accumulator (L5 state assist)
│   └── behaviors/
│       ├── base.py                  # RuleBehavior ABC
│       ├── intrusion.py
│       ├── loitering.py
│       ├── line_crossing.py
│       ├── crowd_density.py
│       └── abandoned_object.py
│
├── alerts/
│   ├── alert_manager.py             # debounce + cooldown + dispatch
│   ├── snapshot.py                  # annotate frame → JPEG
│   ├── clip_recorder.py             # 10s video clip around event
│   └── notifications/
│       ├── base.py                  # NotificationChannel ABC
│       ├── dispatcher.py            # ส่งไปหลาย channel พร้อมกัน
│       ├── line_messaging.py        # LINE Messaging API
│       ├── discord_webhook.py       # Discord Webhook
│       ├── slack_webhook.py         # Slack Incoming Webhook
│       ├── email_sender.py          # SMTP + jinja2
│       ├── webhook_sender.py        # Generic HTTP POST (httpx async)
│       └── mqtt_publisher.py        # paho-mqtt (IoT relay)
│
├── nlq/                             # Natural Language Query (NEW)
│   ├── claude_client.py             # Anthropic API wrapper
│   ├── intent_classifier.py         # query vs command classification
│   ├── query_executor.py            # safe ORM query from params
│   └── response_formatter.py        # results → Thai/English text
│
│  ════════════════════════════════════════════════
│  API CORE  (Central Hub)
│  ════════════════════════════════════════════════
├── api/
│   ├── app.py                       # FastAPI app factory
│   ├── deps.py                      # Depends: db, current_actor, bus
│   ├── middleware/
│   │   ├── auth.py                  # JWT validation + actor injection
│   │   ├── audit.py                 # auto-log every mutating request
│   │   └── rate_limit.py            # per-actor rate limiting
│   ├── routers/
│   │   ├── cameras.py               # /api/cameras/
│   │   ├── zones.py                 # /api/zones/
│   │   ├── rules.py                 # /api/rules/
│   │   ├── events.py                # /api/events/ (filter + search)
│   │   ├── alerts.py                # /api/alerts/ (ack, silence, escalate)
│   │   ├── lpr.py                   # /api/lpr/whitelist/
│   │   ├── users.py                 # /api/users/ (superadmin only)
│   │   ├── api_keys.py              # /api/api-keys/
│   │   ├── analytics.py             # /api/analytics/ (stats, heatmap)
│   │   └── health.py                # /api/health/ (public)
│   └── websocket/
│       ├── hub.py                   # ConnectionManager (multi-client)
│       ├── stream_handler.py        # /ws/stream/{camera_id}
│       └── alert_handler.py         # /ws/alerts (broadcast)
│
│  ════════════════════════════════════════════════
│  DATA LAYER
│  ════════════════════════════════════════════════
├── db/
│   ├── session.py                   # engine + AsyncSessionLocal + get_db()
│   ├── init_db.py                   # create_all() for dev/test
│   └── pragmas.py                   # SQLite WAL + FK pragma
│
├── models/                          # SQLAlchemy ORM (DB-agnostic)
│   ├── __init__.py                  # export all models
│   ├── base.py
│   ├── camera.py
│   ├── zone.py
│   ├── rule.py
│   ├── event.py
│   ├── notification.py
│   ├── lpr_whitelist.py
│   ├── user.py                      # NEW v2
│   ├── api_key.py                   # NEW v2
│   ├── audit_log.py                 # NEW v2
│   └── alert_note.py                # NEW v2
│
├── schemas/                         # Pydantic v2 (API I/O)
│   ├── camera.py
│   ├── zone.py
│   ├── rule.py
│   ├── event.py
│   ├── alert.py
│   ├── user.py                      # NEW v2
│   └── analytics.py
│
├── auth/
│   ├── jwt_handler.py               # encode/decode JWT
│   ├── password.py                  # bcrypt hash/verify
│   └── permissions.py               # permission check functions
│
├── analytics/
│   ├── heatmap.py
│   ├── statistics.py
│   └── report.py
│
├── migrations/                      # Alembic
│   ├── env.py
│   └── versions/
│
├── data/                            # gitignored
│   ├── mtsecurity.db
│   ├── snapshots/
│   ├── clips/
│   └── models/
│
└── tests/
    ├── conftest.py
    ├── unit/
    │   ├── test_mtp_bus.py
    │   ├── test_rule_behaviors.py
    │   ├── test_dwell_tracker.py
    │   ├── test_line_crossing.py
    │   └── test_permissions.py      # NEW v2
    └── integration/
        ├── test_alert_flow.py
        ├── test_api_events.py
        ├── test_actor_permissions.py # NEW v2
        └── test_config_propagation.py # NEW v2
```

---

## 2. Boot Sequence (main.py)

```python
# main.py
async def main():
    cfg = Settings()

    # ── 1. Protocol Layer ──────────────────────────────────────
    bus = MessageBus()
    await bus.start()

    # ── 2. SSOT Layer ──────────────────────────────────────────
    config_svc = ConfigService(db_session_factory, bus)
    state_reg  = StateRegistry()
    await config_svc.initialize()   # load all config → cache

    # ── 3. AI + Ingestion (Thread pool) ────────────────────────
    frame_buf  = FrameBuffer()
    cam_mgr    = CameraManager(frame_buf, config_svc, state_reg, bus)
    await cam_mgr.start_all()

    tracker    = ObjectTracker()
    ai_engine  = InferenceEngine(cfg.model_path, cfg.device)
    pipeline   = AIPipeline(frame_buf, ai_engine, tracker, bus)
    threading.Thread(target=pipeline.run, daemon=True).start()

    # ── 4. Rule Engine ──────────────────────────────────────────
    rule_engine = RuleEngine(config_svc, bus)
    rule_engine.register_all(bus)   # subscribe to TRACK_UPDATE

    # ── 5. Alert Engine ─────────────────────────────────────────
    notif_svc   = NotificationService(cfg)
    alert_mgr   = AlertManager(cache, notif_svc, db_factory, ws_hub, bus)
    alert_mgr.register(bus)         # subscribe to RULE_TRIGGERED

    # ── 6. API Core ─────────────────────────────────────────────
    app = create_app(cfg, config_svc, state_reg, bus)
    await uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=8000)).serve()
```

---

## 3. Dependency Rules (Enforced)

```
protocol/     ← ไม่ import ใครเลย (pure data structures)
ssot/         ← import protocol/, db/, models/
ingestion/    ← import protocol/, ssot/
ai/           ← import protocol/, ssot/, ingestion/
rules/        ← import protocol/, ssot/
alerts/       ← import protocol/, ssot/, db/
api/          ← import protocol/, ssot/, db/, schemas/, auth/
auth/         ← import models/ เท่านั้น
models/       ← import db/base.py เท่านั้น
db/           ← ไม่ import component ใด (pure SQLAlchemy)

✗ ห้าม: ai/ import rules/
✗ ห้าม: rules/ import ai/
✗ ห้าม: ingestion/ import alerts/
✗ ห้าม: models/ import api/
```

---

## 4. Testing Approach (v2)

```python
# tests/conftest.py
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from models.base import Base
from protocol.message_bus import MessageBus

@pytest_asyncio.fixture
async def db():
    """In-memory SQLite — no setup needed, auto-cleanup"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()

@pytest_asyncio.fixture
async def bus():
    """Real MessageBus for integration tests"""
    b = MessageBus()
    await b.start()
    yield b

# Unit test example — test rule behavior in isolation
def test_intrusion_detection():
    from rules.behaviors.intrusion import check_intrusion
    zone_coords = [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]
    assert check_intrusion(centroid=(0.5, 0.5), coords=zone_coords) is True
    assert check_intrusion(centroid=(0.1, 0.1), coords=zone_coords) is False

# Integration test — config change propagates through bus
async def test_config_change_propagates(bus, db):
    received = []
    async def capture(msg): received.append(msg)
    bus.subscribe(MTPMsgType.CONFIG_CHANGED, capture)

    config_svc = ConfigService(lambda: db, bus)
    await config_svc.update_zone(1, {"threshold": 120}, actor="test_admin")

    await asyncio.sleep(0.05)   # let bus dispatch
    assert len(received) == 1
    assert received[0].payload["scope"] == "zone"
```
