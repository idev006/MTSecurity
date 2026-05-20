# MTSecurity v2 — Project Progress Tracker

> อัปเดตล่าสุด: 2026-05-20
> สถานะโดยรวม: **Phase 2 DONE / Phase 3 in progress** — ระบบยังอยู่ระหว่างพัฒนา ไม่ควร deploy production

---

## สถานะปัจจุบัน (Dashboard)

```
Backend   ████████████████████░░░░  82%   stable core, pending: Redis migration, structured logging, metrics
Frontend  █████████████████████░░░  87%   all views done, pending: minor UX polish
Infra     ████████████░░░░░░░░░░░░  52%   Docker up, pending: CI/CD, Prometheus metrics, SSL
Tests     ████████████████░░░░░░░░  65%   182/~280 estimated passing
```

---

## Phase Roadmap

### ✅ Phase 0 — Foundation (DONE)
- [x] Project structure, config, secrets management
- [x] SQLAlchemy async models (User, Camera, Zone, Rule, Event, AuditLog, ...)
- [x] JWT auth (access + refresh tokens), RBAC (SUPERADMIN / ADMIN / OPERATOR / VIEWER)
- [x] Fernet-encrypted RTSP URLs in DB
- [x] MessageBus (MTP protocol) — async pub/sub backbone

### ✅ Phase 1 — Core AI Pipeline (DONE)
- [x] OpenVINO inference engine (YOLO11n)
- [x] ByteTrack-style IoU tracker (vectorized NumPy)
- [x] 3-tier video encoding (THUMBNAIL → AI, MONITOR/DETAIL → stream/evidence)
- [x] CameraThread — RTSP + USB Webcam (hotplug watcher)
- [x] RuleEngine — evaluates all active rules per TRACK_UPDATE
- [x] Behaviors: `intrusion`, `loitering`, `line_crossing`, `crowd_density`, `sudden_gathering`
- [x] Advanced Logic Builder (AND/OR/NOT rule trees)
- [x] ZoneManager — normalized polygon hit-test
- [x] DwellTracker — per-object dwell timing
- [x] ScheduleManager — time-of-day rule activation

### ✅ Phase 2 — Alert & Evidence Pipeline (DONE)
- [x] **FEAT-014**: Frame pinning (EvidenceStore) — snapshot uses exact inference frame
- [x] **FEAT-015**: All-tracks snapshot — annotates every active object in evidence image
- [x] **FEAT-016**: Notification debounce (10 s per-camera) — prevents LINE/Discord storms
- [x] AlertManager — DB event write, WebSocket broadcast, snapshot capture, clip extraction
- [x] Notification channels: LINE Messaging API, Discord Webhook, Slack Webhook

### ✅ Phase 2B — Frontend (DONE)
- [x] Login / Auth with token refresh
- [x] Dashboard (health, camera grid, recent alerts)
- [x] Pilot View (multi-camera monitor, AI bbox overlay SVG, alert feed)
- [x] Cameras View (add RTSP/webcam, MJPEG live thumbnails)
- [x] Zones View (interactive zone drawing on canvas, rule builder UI)
- [x] Events View (filter, acknowledge, silence, escalate, purge)
- [x] Users View (CRUD, role assignment)
- [x] Settings View (system settings, display theme, account)
- [x] DaisyUI 5 themes (dark/light/multiple)
- [x] Real-time WebSocket (alert_fired, camera_state, frame_ready)

### ✅ Phase 2C — Docker Compose (DONE)
- [x] Backend Dockerfile (multi-stage, non-root uid=1001, OpenVINO + FFmpeg)
- [x] Frontend Dockerfile (builder node:20 → runtime nginx:1.27)
- [x] docker-compose.yml (7 services: postgres, redis, backend, frontend, nginx, prometheus, grafana)
- [x] docker-compose.override.yml (dev: Vite hot-reload, ports exposed, mem/cpu bumped)
- [x] nginx reverse proxy (API, WebSocket, MJPEG no-buffer)
- [x] Dev nginx config (proxies to Vite:5173 with HMR WS)
- [x] Grafana + Prometheus provisioning

### 🔄 Phase 3 — Observability (IN PROGRESS)
- [ ] **P3-01** Structured JSON logging (`backend/logging_config.py`)
- [ ] **P3-02** Prometheus `/api/v1/metrics` endpoint (FastAPI + prometheus-client)
- [ ] **P3-03** Grafana dashboard JSON (camera FPS, event rate, AI latency, memory)
- [ ] **P3-04** Alert rules in Prometheus (backend down, high error rate)

### 🔲 Phase 4 — Hardening (TODO)
- [ ] **P4-01** Redis JWT blacklist — replace SQLite `token_blacklist` table
- [ ] **P4-02** Redis rate limiter — replace in-memory slowapi state
- [ ] **P4-03** WebSocket auth fix — JWT in first message body, not URL query param
- [ ] **P4-04** GitHub Actions CI — pytest + ruff + vue-tsc on every PR
- [ ] **P4-05** `.env` secrets rotation guide

### 🔲 Phase 5 — Production Hardening (TODO)
- [ ] **P5-01** SSL/TLS termination (Let's Encrypt / self-signed)
- [ ] **P5-02** Nginx rate limiting (per-IP, per-endpoint)
- [ ] **P5-03** DB backup cron (pg_dump → S3 or local)
- [ ] **P5-04** Health alert notifications (PagerDuty / LINE OA)
- [ ] **P5-05** AI model hot-swap (reload without restart)
- [ ] **P5-06** Horizontal scaling notes (stateless backend behind load balancer)

### 🔲 Phase 6 — Features (TODO / Future)
- [ ] **F6-01** LPR (License Plate Recognition) — model + API stubs exist, logic pending
- [ ] **F6-02** NLQ (Natural Language Query) — directory exists, logic pending
- [ ] **F6-03** Analytics dashboard (hourly/daily event charts)
- [ ] **F6-04** SMTP / Email notifications
- [ ] **F6-05** MQTT notification channel
- [ ] **F6-06** Multi-zone rules (cross-zone logic)
- [ ] **F6-07** Mobile PWA (push notifications via Web Push API)

---

## Test Coverage

| Module | Test File | Count | Status |
|--------|-----------|-------|--------|
| Auth JWT | test_auth.py | 18 | ✅ |
| API Auth endpoints | test_api_auth.py | 12 | ✅ |
| API Camera endpoints | test_api_cameras.py | 14 | ✅ |
| Rule Behaviors | test_rule_behaviors.py | 28 | ✅ |
| Tracker | test_tracker.py | 15 | ✅ |
| Frame Buffer | test_frame_buffer.py | 12 | ✅ |
| Frame Codec | test_frame_codec.py | 10 | ✅ |
| MTP Message Bus | test_mtp_bus.py | 14 | ✅ |
| Dwell Tracker | test_dwell_tracker.py | 12 | ✅ |
| Zone Manager | test_zone_manager.py | 14 | ✅ |
| Schedule Manager | test_schedule_manager.py | 10 | ✅ |
| Permissions | test_permissions.py | 10 | ✅ |
| State Registry | test_state_registry.py | 8 | ✅ |
| WebSocket Hub | test_websocket_hub.py | 8 | ✅ |
| Detector | test_detector.py | 6 | ✅ (mock) |
| Dispatcher | test_dispatcher.py | 8 | ✅ |
| **Evidence Store** | test_evidence_store.py | 10 | ✅ NEW |
| **Alert Debounce** | test_alert_debounce.py | 7 | ✅ NEW |
| Config propagation | test_config_propagation.py | 3 | ✅ |
| **Total** | | **~199 defined / 182 passing** | |

> Note: 17 tests are currently skipped (require OpenVINO model file not present in CI)

---

## Known Issues / Tech Debt

| ID | Description | Priority | Phase |
|----|-------------|----------|-------|
| TD-01 | Redis JWT blacklist not wired — still uses SQLite `token_blacklist` | HIGH | P4-01 |
| TD-02 | WebSocket JWT in URL query param — exposes token in server logs | HIGH | P4-03 |
| TD-03 | No structured logging — plain text logs hard to grep in prod | MED | P3-01 |
| TD-04 | No Prometheus metrics from backend yet | MED | P3-02 |
| TD-05 | `noUnusedLocals` disabled in tsconfig — dead frontend code exists | LOW | cleanup |
| TD-06 | Grafana has provisioning config but no actual dashboard JSON | MED | P3-03 |
| TD-07 | No CI/CD pipeline — tests not run on push | HIGH | P4-04 |
| TD-08 | `.env` contains real secrets in git repo | CRITICAL | P4-05 |

---

## Commit History Summary

| Date | Commit | Description |
|------|--------|-------------|
| 2026-05-20 | 953653f | Docker Compose + FEAT-014/015/016 + test fixes |
| Prior | 0b93f2f | SVG overlay label fixes, Pilot View |
| Prior | — | Initial core system |
