# MTSecurity v2 — Backend Architecture Map

> Generated: 2026-05-15 | Claude Sonnet 4.6
> Purpose: Code navigation reference for development, debugging, and tuning

---

## 1. Directory Tree

```
backend/
├── main.py                          # Bootstrap orchestrator — startup/shutdown sequence
├── config.py                        # Pydantic Settings (loads .env)
│
├── api/
│   ├── app.py                       # FastAPI app factory — CORS, middleware, routers
│   ├── deps.py                      # Dependency injection — DB session, JWT auth, require()
│   ├── middleware/
│   │   └── audit.py                 # AuditMiddleware — logs all POST/PUT/PATCH/DELETE
│   ├── routers/
│   │   ├── auth.py                  # /auth — login, logout, refresh, /me
│   │   ├── users.py                 # /users — CRUD users (SUPERADMIN only)
│   │   ├── cameras.py               # /cameras — CRUD + MJPEG stream + status
│   │   ├── zones.py                 # /zones — CRUD polygons
│   │   ├── rules.py                 # /rules — CRUD behavior rules
│   │   ├── events.py                # /events — list/filter/ack/silence/escalate
│   │   ├── lpr.py                   # /lpr — LPR whitelist management
│   │   ├── health.py                # /health — system health snapshot
│   │   └── simulate.py              # /simulate — test event injection
│   └── websocket/
│       ├── hub.py                   # WebSocketHub — manages client connections, broadcasts
│       └── router.py                # /ws — WebSocket endpoint (JWT via ?token=)
│
├── auth/
│   ├── jwt_handler.py               # create/decode tokens, blacklist, purge
│   ├── password.py                  # hash, verify, validate policy
│   └── permissions.py               # 6-role RBAC matrix
│
├── db/
│   ├── session.py                   # AsyncSession factory, get_db() dependency
│   ├── pragmas.py                   # SQLite pragmas (WAL mode, etc.)
│   └── init_db.py                   # create_tables() + idempotent migrations
│
├── models/                          # SQLAlchemy ORM models
│   ├── base.py                      # DeclarativeBase + TimestampMixin
│   ├── user.py                      # User
│   ├── camera.py                    # Camera
│   ├── zone.py                      # Zone
│   ├── event.py                     # Event (alert record)
│   ├── rule.py                      # Rule (detection rule)
│   ├── notification.py              # Notification (sent record)
│   ├── api_key.py                   # APIKey
│   ├── audit_log.py                 # AuditLog
│   ├── alert_note.py                # AlertNote (operator comments)
│   ├── token_blacklist.py           # TokenBlacklist (replaces Redis)
│   └── lpr_whitelist.py             # LPRWhitelist (plate numbers)
│
├── schemas/                         # Pydantic request/response shapes
│   ├── user.py
│   ├── camera.py
│   ├── zone.py                      # Also contains RuleCreate/Read, LogicNode
│   ├── event.py                     # EventFilter — pagination + all filters
│   └── analytics.py
│
├── ssot/                            # Single Source of Truth
│   ├── state_registry.py            # In-memory runtime state (thread-safe)
│   └── config_service.py            # DB-backed SSOT with 60s TTL cache
│
├── protocol/                        # Internal messaging
│   ├── mtp.py                       # MTPMessage, MTPPriority, MTPMsgType
│   ├── message_bus.py               # AsyncIO priority queue + pub/sub
│   └── payloads.py                  # Typed payload schemas per message type
│
├── ingestion/                       # Camera frame capture
│   ├── camera_manager.py            # Lifecycle: start/stop/restart CameraThreads
│   ├── camera_thread.py             # One thread per camera, cv2 read loop, backoff
│   ├── frame_buffer.py              # Thread-safe 1-slot circular buffer per camera
│   ├── frame_codec.py               # JPEG encode/decode
│   ├── webcam_enumerator.py         # Enumerate local device indices 0–9
│   └── webcam_watcher.py            # Hotplug monitor — device add/remove
│
├── ai/
│   ├── pipeline.py                  # AIPipeline — round-robin inference, WIP=2
│   ├── detector.py                  # postprocess_yolo() → Detection objects
│   ├── inference_engine.py          # OpenVINO wrapper
│   ├── model_registry.py            # Load model to CPU/GPU/AUTO
│   ├── tracker.py                   # Object tracker (multi-camera)
│   ├── session_registry.py          # Track active track_ids per camera
│   └── lpr/__init__.py              # LPR model integration
│
├── rules/
│   ├── rule_engine.py               # Evaluates rules on TRACK_UPDATE
│   ├── behaviors/
│   │   ├── base.py                  # RuleBehavior ABC, TriggerResult
│   │   ├── intrusion.py
│   │   ├── loitering.py
│   │   ├── line_crossing.py
│   │   ├── crowd_density.py
│   │   └── abandoned_object.py
│   ├── dwell_tracker.py             # Accumulate dwell time per track
│   ├── zone_manager.py              # Point-in-polygon checks
│   ├── schedule_manager.py          # Time-based rule enable/disable
│   └── logic_validator.py           # Evaluate AND/OR/NOT logic trees
│
├── alerts/
│   ├── alert_manager.py             # Persist Event, snapshot, dispatch notif
│   ├── snapshot.py                  # Capture + annotate frame as JPEG
│   └── notifications/
│       ├── base.py                  # NotificationChannel ABC, AlertPayload
│       ├── dispatcher.py            # Concurrent multi-channel send
│       ├── email_sender.py
│       ├── slack_webhook.py
│       ├── discord_webhook.py
│       ├── line_messaging.py
│       ├── mqtt_publisher.py
│       └── webhook_sender.py
│
└── tests/
    ├── unit/                        # pytest-asyncio unit tests per module
    └── integration/                 # End-to-end config propagation tests
```

---

## 2. Startup Sequence (main.py)

```
python main.py
    │
    ├─ 1. load Settings from .env (Pydantic BaseSettings)
    ├─ 2. init StateRegistry (boot_state = "INITIALIZING")
    ├─ 3. start MessageBus  (async priority queue)
    ├─ 4. init DB engine + create tables + run migrations
    ├─ 5. init ConfigService  (warm cache from DB)
    ├─ 6. start CameraManager  (start one CameraThread per active camera)
    ├─ 7. start WebcamWatcher  (hotplug daemon)
    ├─ 8. start AIPipeline  (daemon thread, WIP semaphore=2)
    ├─ 9. start RuleEngine  (subscribes TRACK_UPDATE)
    ├─ 10. start AlertManager  (subscribes RULE_TRIGGERED)
    ├─ 11. create FastAPI app + attach all services to app.state
    ├─ 12. set boot_state = "RUNNING"
    └─ 13. uvicorn.serve()  (blocking)
```

**Services accessible via `request.app.state`:**
| Key | Type | Purpose |
|-----|------|---------|
| `cfg` | Settings | All config values |
| `config_svc` | ConfigService | DB-backed SSOT |
| `state_reg` | StateRegistry | Runtime camera/system state |
| `bus` | MessageBus | Internal pub/sub |
| `ws_hub` | WebSocketHub | WebSocket client manager |
| `cam_manager` | CameraManager | Start/stop cameras |
| `frame_buffer` | FrameBuffer | Latest frame per camera |
| `rule_engine` | RuleEngine | Evaluates rules on tracks |
| `alert_manager` | AlertManager | Persists + notifies alerts |

---

## 3. API Endpoints Reference

All endpoints prefixed `/api/v1`. Auth via `Authorization: Bearer <access_token>`.

### Auth
| Method | Path | Permission | Body/Params | Returns |
|--------|------|------------|-------------|---------|
| POST | `/auth/login` | Public | `{username, password}` | `TokenResponse` |
| POST | `/auth/logout` | Authenticated | — | 204 |
| POST | `/auth/refresh` | Public | `{refresh_token}` | `TokenResponse` |
| GET | `/auth/me` | Authenticated | — | `UserRead` |

### Cameras
| Method | Path | Permission | Notes |
|--------|------|------------|-------|
| GET | `/cameras` | cameras:read | Scoped by user.camera_scope |
| POST | `/cameras` | cameras:create | RTSP URL encrypted (Fernet) |
| GET | `/cameras/{id}` | cameras:read | |
| PATCH | `/cameras/{id}` | cameras:update | Triggers hot-reload via ConfigService |
| DELETE | `/cameras/{id}` | cameras:delete | |
| GET | `/cameras/{id}/status` | cameras:read | Returns `CameraStatus` (state, fps, latency) |
| GET | `/cameras/{id}/stream` | cameras:stream | MJPEG `StreamingResponse`, auth via `?token=` |
| GET | `/cameras/webcams` | cameras:read | List device indices 0–9 |

### Events
| Method | Path | Permission | Notes |
|--------|------|------------|-------|
| GET | `/events` | events:read | Filter: severity, status, behavior, camera_id, from_dt, to_dt, **page, page_size** |
| GET | `/events/{id}` | events:read | |
| GET | `/events/{id}/snapshot` | events:read | Returns JPEG FileResponse |
| POST | `/events/{id}/acknowledge` | alerts:acknowledge | Body: `{note?}` |
| POST | `/events/{id}/silence` | alerts:silence | Body: `{duration_seconds}` |
| POST | `/events/{id}/escalate` | alerts:escalate | Body: `{reason}` |
| POST | `/events/{id}/notes` | events:read | Body: `{body}` |

### Zones / Rules / LPR
| Method | Path | Notes |
|--------|------|-------|
| GET/POST/PATCH/DELETE | `/zones` | Zone coords stored as JSON (normalized 0–1) |
| GET/POST/PATCH/DELETE | `/rules` | Behavior + thresholds + schedule + logic tree |
| GET/POST/DELETE | `/lpr` | Plate whitelist |

### WebSocket
```
ws://host/api/v1/ws?token=<access_token>

Client → Server:
  {"type": "subscribe", "camera_ids": [1, 2]}  // empty = all

Server → Client:
  {"type": "alert_fired",    "data": {...}}
  {"type": "track_update",   "camera_id": 1, "data": {...}}
  {"type": "frame_ready",    "camera_id": 1, "data": {...}}
  {"type": "health_beat",    "data": {...}}
```

---

## 4. Database Models

```
User ─────────────┬─── APIKey
                  └─── AuditLog

Camera ───────────┬─── Zone ──────┬─── Rule ──── Event ──┬── AlertNote
                  │               │                       └── Notification
                  └─── Event      └─── Event

TokenBlacklist  (standalone — jti PK)
LPRWhitelist    (standalone — plate unique)
```

### Key Model Fields

**Event** (most queried model):
```python
id, camera_id, rule_id, behavior, severity, confidence, track_id,
snapshot_path, clip_path, occurred_at, acknowledged_at, acknowledged_by,
silenced_until, status ("NEW"|"ACKNOWLEDGED"|"SILENCED"|"ESCALATED"),
metadata_json
```

**Rule** (controls detection behavior):
```python
id, zone_id, name, behavior, is_active,
confidence_threshold,    # float, e.g. 0.6
dwell_threshold_seconds, # for loitering
cooldown_seconds,        # prevent duplicate alerts
severity,                # "low"|"medium"|"high"|"critical"
schedule,                # JSON: {"enabled": true, "windows": [{"days": [1..7], "start": "09:00", "end": "18:00"}]}
logic                    # JSON: LogicNode tree (AND/OR/NOT of conditions)
```

---

## 5. Authentication & RBAC

### Roles (highest → lowest privilege)
```
SYSTEM > SUPERADMIN > ADMIN > OPERATOR > AUDITOR > EXTERNAL_SYSTEM
```

### Permission Matrix (summary)
| Permission | Roles |
|-----------|-------|
| users:* | SUPERADMIN |
| cameras:create/update/delete | SUPERADMIN, ADMIN |
| cameras:read/stream | SUPERADMIN, ADMIN, OPERATOR, AUDITOR |
| zones/rules:create/delete | SUPERADMIN, ADMIN |
| events:read | SUPERADMIN, ADMIN, OPERATOR, AUDITOR |
| alerts:acknowledge | SUPERADMIN, ADMIN, OPERATOR |
| alerts:silence | SUPERADMIN, ADMIN |
| alerts:escalate | SUPERADMIN, ADMIN, OPERATOR |
| lpr:* | SUPERADMIN, ADMIN |

### JWT Flow
```
Login → access_token (60 min, HS256) + refresh_token (7 days)
Request → Authorization: Bearer <access_token>
Refresh → POST /auth/refresh with refresh_token → new pair
Logout → jti added to TokenBlacklist (purged on next login)
```

### Camera Scope (per-user access control)
```python
user.camera_scope = "1,3,5"  # comma-separated camera IDs, NULL = all cameras
user.camera_ids() → [1, 3, 5]  # parsed
# Applied automatically in cameras.router list and events.router list
```

---

## 6. Internal Message Bus (protocol/)

### Message Types Reference
| Type | Priority | Publisher | Subscriber(s) |
|------|----------|-----------|---------------|
| `FRAME_READY` | NORMAL | CameraThread | AIPipeline, WebSocketHub |
| `TRACK_UPDATE` | NORMAL | AIPipeline | RuleEngine, WebSocketHub |
| `RULE_TRIGGERED` | HIGH | RuleEngine | AlertManager |
| `ALERT_FIRED` | HIGH | AlertManager | WebSocketHub |
| `CONFIG_CHANGED` | NORMAL | ConfigService | CameraManager, RuleEngine |
| `CAMERA_STATUS` | NORMAL | CameraThread | StateRegistry, WebSocketHub |
| `HEALTH_BEAT` | LOW | HealthMonitor | WebSocketHub |
| `SYSTEM_SHUTDOWN` | CRITICAL | main.py | All services |

### Publish Pattern
```python
msg = MTPMessage(
    msg_type=MTPMsgType.ALERT_FIRED,
    payload=payload.model_dump(),
    priority=MTPPriority.HIGH,
    source="alert_manager",
    ttl_seconds=30.0,
)
await bus.publish(msg)
```

### Subscribe Pattern
```python
bus.subscribe(MTPMsgType.TRACK_UPDATE, self._on_track_update)

async def _on_track_update(self, msg: MTPMessage) -> None:
    payload = TrackUpdatePayload(**msg.payload)
    # ... process
```

---

## 7. Data Flow (End-to-End)

```
Camera Source (RTSP / Webcam)
        │
        ▼
CameraThread.read_loop()
  └─ encode JPEG → FrameBuffer.put()
  └─ publish FRAME_READY
        │
        ▼
AIPipeline._process_frame()
  └─ decode JPEG → letterbox → OpenVINO inference
  └─ postprocess_yolo() → Detection[]
  └─ ObjectTracker.update() → Track[] (with track_id)
  └─ publish TRACK_UPDATE {camera_id, tracks[]}
        │
        ▼
RuleEngine._on_track_update()
  └─ for each track:
      └─ ZoneManager: is centroid inside zone?
      └─ DwellTracker: how long has track been in zone?
      └─ ScheduleManager: is rule active now?
      └─ LogicValidator: evaluate AND/OR/NOT tree
      └─ check cooldown (rule_id, track_id)
      └─ if triggered → publish RULE_TRIGGERED
        │
        ▼
AlertManager._on_rule_triggered()
  └─ persist Event to DB (status=NEW)
  └─ capture snapshot from FrameBuffer → annotate → save JPEG
  └─ NotificationDispatcher.dispatch() → concurrent sends:
      ├─ Email (SMTP)
      ├─ Slack webhook
      ├─ Discord webhook
      ├─ LINE Channel API
      └─ MQTT publish
  └─ publish ALERT_FIRED
        │
        ▼
WebSocketHub.broadcast_alert()
  └─ send to all connected browser clients
        │
        ▼
Frontend: useEventsStore / PilotView real-time update
```

---

## 8. Configuration System

### Environment Variables (.env)
```bash
# Required
JWT_SECRET_KEY=<min-32-chars-random-string>
ENCRYPTION_KEY=<Fernet-base64-key>

# Optional (defaults shown)
DATABASE_URL=sqlite+aiosqlite:///./data/mtsecurity.db
HOST=0.0.0.0
PORT=8000
AI_MODEL_PATH=./data/models/yolo11n.xml
AI_MODEL_DEVICE=CPU              # CPU | GPU | AUTO
AI_CONFIDENCE_THRESHOLD=0.6

# Notifications (all optional)
LINE_CHANNEL_ACCESS_TOKEN=
DISCORD_WEBHOOK_URL=
SLACK_WEBHOOK_URL=
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=

# Base URL for snapshot links
BASE_URL=http://localhost:8000
```

### Hot-Reload Flow (no restart needed)
```
User changes camera config via PATCH /cameras/{id}
    → cameras.router calls config_svc.update_camera()
    → ConfigService updates DB
    → ConfigService invalidates TTL cache
    → ConfigService publishes CONFIG_CHANGED on bus
    → CameraManager._on_config_changed() restarts thread if needed
    → RuleEngine._on_config_changed() reloads rule config
```

---

## 9. Concurrency Model

```
Main Thread (asyncio event loop)
├── FastAPI / uvicorn (HTTP + WebSocket)
├── MessageBus dispatch loop (async task)
├── ConfigService (async)
├── WebSocketHub (async)
└── AlertManager / RuleEngine (async, subscribed to bus)

Camera Threads (threading.Thread, daemon=True)
├── CameraThread[cam_1]  (blocking cv2.VideoCapture)
├── CameraThread[cam_2]
└── ...

AI Thread (threading.Thread, daemon=True)
└── AIPipeline._run()
    └── WIP semaphore (max 2 concurrent inference tasks)
    └── asyncio.run_coroutine_threadsafe(bus.publish()) → bridge to main loop

Cross-thread communication:
├── CameraThread → FrameBuffer (threading.Lock)
├── AIPipeline → FrameBuffer (threading.Lock, read-only)
└── Any thread → MessageBus (asyncio.run_coroutine_threadsafe)
```

---

## 10. Key Files to Know When Debugging

| Symptom | First Files to Check |
|---------|---------------------|
| Camera not streaming | `ingestion/camera_thread.py` (backoff logic), `ingestion/frame_buffer.py` |
| AI detections not showing | `ai/pipeline.py` (WIP limit?), `ai/detector.py` (confidence threshold?) |
| Rules not triggering | `rules/rule_engine.py` (cooldown? zone check?), `rules/zone_manager.py` |
| Alerts not sent | `alerts/alert_manager.py`, `alerts/notifications/dispatcher.py` |
| WebSocket dropping | `api/websocket/hub.py` (disconnect handling) |
| Auth failing | `auth/jwt_handler.py` (decode errors), `api/deps.py` (get_current_user) |
| API filters ignored | `api/routers/<router>.py` — check dependency uses `Depends()` not `= None` ← **known bug class** |
| Notification not delivered | `alerts/notifications/<channel>.py`, check .env variables |
| High CPU | `ai/pipeline.py` (poll interval, WIP limit), `ingestion/camera_thread.py` (fps throttle) |
| DB growing fast | `models/event.py` (cleanup?), `models/notification.py` (log records) |

---

## 11. Testing

```bash
# Run all tests
cd backend && pytest

# Run specific module
pytest tests/unit/test_rule_behaviors.py -v

# With coverage
pytest --cov=. --cov-report=html

# Integration only
pytest tests/integration/ -v
```

**Test files per module:**
- `test_auth.py` — JWT create/decode/blacklist
- `test_permissions.py` — RBAC matrix
- `test_mtp_bus.py` — message bus pub/sub, priority, TTL
- `test_frame_buffer.py` — thread-safe frame operations
- `test_detector.py` — YOLO postprocess logic
- `test_tracker.py` — object tracking across frames
- `test_rule_behaviors.py` — each behavior type
- `test_dispatcher.py` — notification dispatch + failure handling
- `test_api_auth.py` — login/logout/refresh endpoints
- `test_api_cameras.py` — camera CRUD + stream
- `test_websocket_hub.py` — client connect/disconnect/broadcast

---

## 12. Performance Tuning Points

| Setting | Location | Default | Notes |
|---------|----------|---------|-------|
| AI WIP limit | `ai/pipeline.py` `_WIP_LIMIT` | 2 | Increase on multi-core CPU |
| AI poll interval | `ai/pipeline.py` `_POLL_INTERVAL` | 1/30 s | 30 Hz inference rate |
| Camera FPS | `config.py` `stream_thumbnail_fps` | 3 fps | For MJPEG stream |
| AI confidence | `config.py` `ai_confidence_threshold` | 0.6 | Lower → more detections |
| Rule cooldown | `models/rule.py` `cooldown_seconds` | 60 s | Per rule in DB |
| JWT expiry | `config.py` `jwt_access_token_expire_minutes` | 60 min | |
| Config cache TTL | `ssot/config_service.py` TTLCache | 60 s | Reduce for faster hot-reload |
| DB WAL mode | `db/pragmas.py` | enabled | Better concurrent reads |
| RTSP reconnect max | `ingestion/camera_thread.py` | 10 tries | Adjust for unreliable networks |
| Snapshot retention | `config.py` `max_snapshot_age_days` | 30 days | Disk cleanup |
