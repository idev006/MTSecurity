# MTSecurity v2 — AI Video Management System

ระบบกล้องวงจรปิดอัจฉริยะพร้อม AI Detection, Real-time Alerts, Pilot Console และ Admin UI ครบชุด

> **⚠️ สถานะ:** กำลังพัฒนา Phase 3 — ไม่แนะนำสำหรับ production ยังขาด Redis migration, structured logging, CI/CD  
> ดูสถานะโดยละเอียด: [doc/PROGRESS.md](doc/PROGRESS.md)

---

## Quick Start (Docker — แนะนำ)

```bash
# 1. ตั้งค่า secrets (ครั้งแรกเท่านั้น)
cp .env.example .env              # แก้ไข POSTGRES_PASSWORD, GF_SECURITY_ADMIN_PASSWORD

# 2. Build images (ครั้งแรก หรือเมื่อ Dockerfile/dependencies เปลี่ยน)
docker compose build

# 3. Start
docker compose up -d

# 4. ดู logs
docker compose logs -f
```

เปิด browser: **http://localhost**

> **Rebuild rule:** ใช้ `docker compose up -d` เท่านั้นในการใช้งานประจำวัน  
> `--build` ใช้เฉพาะเมื่อ `Dockerfile`, `requirements.txt`, หรือ `package.json` เปลี่ยน

---

## Services

| Service | URL | คำอธิบาย |
|---------|-----|---------|
| **App** | http://localhost | Vue SPA ผ่าน nginx |
| **Frontend (dev)** | http://localhost:5173 | Vite dev server (hot-reload) |
| **API Docs** | http://localhost/api/docs | Swagger (DEBUG=true เท่านั้น) |
| **Grafana** | http://localhost:3000 | Metrics dashboard |
| **PostgreSQL** | localhost:5432 | Dev only (exposed) |
| **Redis** | localhost:6379 | Dev only (exposed) |

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 async, PostgreSQL / SQLite |
| AI | OpenVINO YOLO11n, ByteTrack-style IoU tracker |
| Video | OpenCV, FFmpeg |
| Frontend | Vue 3, TypeScript, Vite 6, DaisyUI 5, Pinia |
| Real-time | WebSocket, MJPEG stream |
| Auth | JWT HS256, Fernet encryption, RBAC |
| Infra | Docker Compose, nginx, Prometheus, Grafana |
| Tests | pytest-asyncio (182 passing) |

---

## Project Structure

```
my_workspace/
├── backend/                    FastAPI + Python
│   ├── ai/                     OpenVINO inference, YOLO detector, tracker, pipeline
│   ├── alerts/                 AlertManager, snapshot, clip, notification channels
│   │   └── notifications/      LINE, Discord, Slack, SMTP, MQTT, Webhook
│   ├── api/
│   │   ├── middleware/         AuditLog middleware
│   │   ├── routers/            auth, cameras, zones, rules, events, users, system, health
│   │   └── websocket/          hub, router
│   ├── auth/                   JWT, password hash, RBAC permissions
│   ├── db/                     SQLAlchemy session, init_db, pragmas
│   ├── ingestion/              CameraThread, CameraManager, FrameBuffer,
│   │                           ClipBuffer, EvidenceStore, WebcamWatcher
│   ├── models/                 Camera, Zone, Rule, Event, User, AuditLog, ...
│   ├── protocol/               MessageBus (MTP pub/sub)
│   ├── rules/                  RuleEngine, ZoneManager, DwellTracker
│   │   └── behaviors/          intrusion, loitering, line_crossing, crowd_density, ...
│   ├── schemas/                Pydantic v2 schemas
│   ├── ssot/                   ConfigService, StateRegistry
│   ├── tests/                  unit/ + integration/ (199 test functions)
│   ├── Dockerfile              Multi-stage build (builder → runtime, uid=1001)
│   └── .env.docker             Docker env (secrets)
│
├── frontend/                   Vue 3 + TypeScript + DaisyUI 5
│   ├── src/
│   │   ├── api/                client.ts — typed API wrappers
│   │   ├── components/         AppLayout, RuleLogicBuilder, ZoneCanvas, SchedulePicker
│   │   ├── stores/             auth, cameras, zones, events, system, toast (Pinia)
│   │   └── views/              Login, Dashboard, Pilot, Cameras, Zones, Events, Users, Settings
│   └── Dockerfile              node:20-alpine build → nginx:1.27-alpine runtime
│
├── nginx/
│   ├── nginx.conf              Base nginx config
│   └── conf.d/
│       ├── mtsecurity.conf     Production (→ frontend:80)
│       └── mtsecurity.dev.conf Development (→ frontend:5173 + Vite HMR)
│
├── prometheus/
│   └── prometheus.yml          Scrape config (backend:8000/metrics, postgres, redis exporters)
│
├── grafana/
│   └── provisioning/           Datasource + dashboard auto-provisioning
│
├── doc/
│   ├── PROGRESS.md             Project progress, roadmap, tech debt ← อ่านนี้ก่อน
│   ├── DEPLOY.md               Deployment guide (dev + production) ← คู่มือ deploy
│   ├── BUGFIX_LOG.md           Bug + feature history
│   └── MASTER_BLUEPRINT_BIBLE.md  Architecture philosophy
│
├── docker-compose.yml          Production stack (7 services)
├── docker-compose.override.yml Dev overrides (Vite, exposed ports, more memory)
├── .env                        Root secrets (postgres, grafana) — ❌ do not commit
└── README.md                   ไฟล์นี้
```

---

## Cameras

| ประเภท | วิธีเพิ่ม | ตัวอย่าง |
|--------|---------|---------|
| IP Camera / NVR | RTSP URL | `rtsp://admin:pass@192.168.1.100:554/stream` |
| USB Webcam | Device Index 0–9 | กด "+ WEBCAM" ในหน้า Cameras |

ระบบ Hotplug Watcher ตรวจสอบ USB webcam ทุก 15 วินาที

---

## Roles & Permissions

| Role | สิทธิ์ |
|------|--------|
| `SUPERADMIN` | ทุกอย่าง รวมถึงจัดการ users, ลบข้อมูล |
| `ADMIN` | จัดการกล้อง/zones/rules, ดู events, ตั้งค่าระบบ |
| `OPERATOR` | ดูกล้องที่ได้รับมอบหมาย, ยืนยัน/ปิดเสียง events |
| `VIEWER` | ดูอย่างเดียว |

---

## AI Behaviors

| Behavior | คำอธิบาย |
|----------|---------|
| `intrusion` | ตรวจจับการบุกรุกเข้าโซน |
| `loitering` | ตรวจจับการซุ่มรอนานเกินกำหนด |
| `line_crossing` | ตรวจจับการข้ามเส้น (directional) |
| `crowd_density` | ตรวจจับฝูงชนเกินจำนวนที่กำหนด |
| `sudden_gathering` | ตรวจจับการรวมตัวกะทันหัน |

สร้าง Rule แบบ Advanced ด้วย Logic Tree (AND / OR / NOT) ผสม behaviors ได้อิสระ

---

## Video Quality Tiers

```
raw frame (RTSP)
  ├─ THUMBNAIL  320×180 q60   → frame_buffer  → AI Pipeline (low latency)
  ├─ evidence_tier*            → hires_buffer  → Snapshot + Clip (quality)
  └─ stream_tier*              → stream_buffer → MJPEG Live Stream
```

ปรับ tier ได้ผ่าน Settings → ระบบ โดยไม่ต้อง restart

---

## Notification Channels

ตั้งค่าใน `backend/.env.docker`:

```env
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_CHANNEL_ID=...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

Notification debounce: 10 วินาทีต่อกล้อง (ป้องกัน spam เมื่อมีหลาย object ใน frame)

---

## API Reference

Base: `/api/v1/`

| Group | Endpoints |
|-------|-----------|
| Auth | `POST /auth/login`, `POST /auth/logout`, `POST /auth/refresh`, `GET /auth/me` |
| Cameras | `GET/POST /cameras`, `PATCH/DELETE /cameras/{id}`, `GET /cameras/{id}/stream` |
| Zones | `GET/POST /zones`, `PATCH/DELETE /zones/{id}`, `POST /zones/{id}/enable|disable` |
| Rules | `GET/POST /rules`, `PATCH/DELETE /rules/{id}`, `POST /rules/{id}/enable|disable` |
| Events | `GET /events`, `POST /events/{id}/acknowledge|silence|escalate`, `POST /events/purge` |
| Users | `GET/POST /users`, `PATCH/DELETE /users/{id}` |
| System | `GET/PATCH /system/settings` |
| Other | `GET /health`, `WS /ws?token=JWT` |

ดูรายละเอียดทั้งหมด: http://localhost/api/docs (ต้องตั้ง `DEBUG=true`)

---

## Documentation

| เอกสาร | คำอธิบาย |
|--------|---------|
| [doc/PROGRESS.md](doc/PROGRESS.md) | สถานะโครงการ, roadmap, known issues |
| [doc/DEPLOY.md](doc/DEPLOY.md) | คู่มือ deployment ฉบับสมบูรณ์ |
| [doc/HTTPS.md](doc/HTTPS.md) | HTTPS setup: Cloudflare Tunnel, mkcert LAN SSL |
| [doc/BUGFIX_LOG.md](doc/BUGFIX_LOG.md) | ประวัติ bug fix และ feature |
| [doc/MASTER_BLUEPRINT_BIBLE.md](doc/MASTER_BLUEPRINT_BIBLE.md) | หลักการออกแบบ |
