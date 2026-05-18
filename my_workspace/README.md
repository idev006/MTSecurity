# MTSecurity — AI Video Management System

ระบบกล้องวงจรปิดอัจฉริยะพร้อม AI Detection, Real-time Alerts, Pilot's Console และ Admin UI ครบชุด

---

## Quick Start (Windows)

```
start-all.bat          เริ่ม Backend + Frontend พร้อมกัน (สองหน้าต่าง)
start-backend.bat      เริ่มเฉพาะ Backend  → http://localhost:8000
start-frontend.bat     เริ่มเฉพาะ Frontend → http://localhost:5173
```

---

## Prerequisites

| Software | Version | Download |
|---|---|---|
| Python | 3.11+ | python.org |
| Node.js | 18+ | nodejs.org |
| FFmpeg | 6+ | ffmpeg.org |
| OpenCV-Python | (auto via pip) | — |

---

## Setup (ครั้งแรกเท่านั้น)

### 1. Backend

```bat
:: สร้าง virtualenv (ทำครั้งเดียว)
python -m venv D:\dev\MTSecurity\my_env
D:\dev\MTSecurity\my_env\Scripts\pip install -r my_workspace\backend\requirements.txt

:: ตั้งค่า env
copy my_workspace\backend\.env.example my_workspace\backend\.env
```

แก้ไข `backend\.env`:
```env
JWT_SECRET_KEY=สุ่มอย่างน้อย 32 ตัวอักษร
ENCRYPTION_KEY=สร้างด้วย Fernet.generate_key()
FFMPEG_PATH=D:\libs\ffmpeg\bin\ffmpeg.exe
```

สร้าง keys ด้วย:
```bat
D:\dev\MTSecurity\my_env\Scripts\python -c "import secrets; print(secrets.token_hex(32))"
D:\dev\MTSecurity\my_env\Scripts\python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### 2. Frontend

```bat
cd frontend
npm install
copy .env.example .env
```

---

## รันในโหมด Development

```bat
start-all.bat
```

เปิด browser: **http://localhost:5173**

| Service | URL | หมายเหตุ |
|---|---|---|
| Frontend | http://localhost:5173 | Vue SPA (Vite dev server) |
| Backend API | http://localhost:8000 | FastAPI |
| API Docs | http://localhost:8000/api/docs | Swagger UI (debug mode เท่านั้น) |
| WebSocket | ws://localhost:8000/api/v1/ws | Real-time events |

---

## โครงสร้างโปรเจกต์

```
my_workspace/
├── backend/                    FastAPI + Python
│   ├── api/
│   │   ├── middleware/         audit.py — AuditLog บันทึกทุก action
│   │   ├── routers/            auth, cameras, zones, rules, events,
│   │   │                       users, system, lpr, simulate, health
│   │   └── websocket/          hub.py, router.py
│   ├── ai/                     OpenVINO inference, detector, tracker, pipeline
│   ├── alerts/                 AlertManager, snapshot, clip, notifications
│   │   └── notifications/      LINE, Discord, Slack, SMTP, MQTT, Webhook
│   ├── auth/                   JWT handler, password hash, RBAC permissions
│   ├── db/                     SQLAlchemy session, pragmas, init_db
│   ├── ingestion/              CameraThread (RTSP + Webcam), CameraManager,
│   │                           FrameBuffer, ClipBuffer, WebcamWatcher
│   ├── models/                 Camera, Zone, Rule, Event, User, AuditLog,
│   │                           SystemSetting, LPRPlate
│   ├── protocol/               MessageBus (MTP), payloads
│   ├── rules/                  RuleEngine, ZoneManager, DwellTracker,
│   │   └── behaviors/          intrusion, loitering, crowd_density,
│   │                           running, abandoned_object, …
│   ├── schemas/                Pydantic v2 request/response schemas
│   ├── ssot/                   StateRegistry, ConfigService
│   ├── tests/                  unit/ + integration/
│   ├── config.py               Settings (pydantic-settings, reads .env)
│   ├── .env.example            Template env vars
│   └── requirements.txt
│
├── frontend/                   Vue 3 + TypeScript + DaisyUI 5
│   ├── src/
│   │   ├── api/                client.ts — typed API wrappers
│   │   ├── components/         AppLayout.vue (navbar + sidebar + statusbar)
│   │   ├── router/             index.ts — auth guards + role guards
│   │   ├── stores/             auth, cameras, zones, events, system, toast (Pinia)
│   │   ├── utils/              time.ts — UTC-safe datetime helpers
│   │   └── views/              Login, Dashboard, Pilot, Cameras, Zones,
│   │                           Events, Users, Settings
│   ├── .env.example
│   └── vite.config.ts          Proxy /api → backend
│
├── scripts/
│   ├── install-services.ps1    ติดตั้ง NSSM Windows Service
│   └── check-startup.ps1       ตรวจสอบ environment ก่อนเริ่ม
│
├── doc/
│   ├── BUGFIX_LOG.md           บันทึก bug + feature ทุกรายการ
│   └── MASTER_BLUEPRINT_BIBLE.md  หลักการออกแบบโครงการ
│
├── nginx.conf                  Reverse proxy config (production)
├── start-all.bat               รันทั้งระบบ (dev)
├── start-backend.bat           รันเฉพาะ backend
├── start-frontend.bat          รันเฉพาะ frontend
└── README.md                   ไฟล์นี้
```

---

## กล้องที่รองรับ

| ประเภท | วิธีเพิ่ม | ตัวอย่าง |
|---|---|---|
| **IP Camera / NVR** | RTSP URL | `rtsp://admin:pass@192.168.1.100:554/stream` |
| **USB Webcam** | Device Index 0-9 | กด "+ WEBCAM" ในหน้า Cameras |

USB Webcam รองรับสูงสุด 10 ตัว (device index 0-9) ต่อเครื่อง  
Webcam Hotplug Watcher ตรวจสอบทุก 15 วินาที และ remap device index อัตโนมัติ

---

## Roles & Permissions

| Role | สิทธิ์ |
|---|---|
| `SUPERADMIN` | ทุกอย่าง รวมถึงลบกล้อง, จัดการ users, ลบ events |
| `ADMIN` | จัดการกล้อง/zones/rules, ดู events, ตั้งค่าระบบ |
| `OPERATOR` | ดูกล้องที่ได้รับมอบหมาย, ยืนยัน/ปิดเสียง events |
| `VIEWER` | ดูอย่างเดียว |

---

## API Overview

Base path: `/api/v1/`

### Auth
| Method | Endpoint | คำอธิบาย |
|---|---|---|
| POST | `/auth/login` | รับ access + refresh token |
| POST | `/auth/logout` | revoke access + refresh token |
| POST | `/auth/refresh` | ต่ออายุ token |
| GET | `/auth/me` | ข้อมูล user ปัจจุบัน |

### Cameras
| Method | Endpoint | คำอธิบาย |
|---|---|---|
| GET | `/cameras` | รายการกล้อง |
| POST | `/cameras` | เพิ่มกล้อง (RTSP หรือ Webcam) |
| PATCH | `/cameras/{id}` | แก้ไขกล้อง |
| DELETE | `/cameras/{id}` | ลบกล้อง |
| POST | `/cameras/{id}/enable` | เปิดกล้อง (cascade zones + rules) |
| POST | `/cameras/{id}/disable` | ปิดกล้อง (cascade zones + rules) |
| GET | `/cameras/{id}/status` | สถานะ runtime (FPS, latency, state) |
| GET | `/cameras/{id}/stream` | MJPEG live stream (`?token=JWT`) |
| GET | `/cameras/webcams` | scan USB webcam ที่เชื่อมต่ออยู่ |

### Zones & Rules
| Method | Endpoint | คำอธิบาย |
|---|---|---|
| GET | `/zones` | รายการ zones |
| POST | `/zones` | สร้าง zone |
| PATCH | `/zones/{id}` | แก้ไข zone |
| DELETE | `/zones/{id}` | ลบ zone |
| POST | `/zones/{id}/enable` | เปิด zone (cascade rules) |
| POST | `/zones/{id}/disable` | ปิด zone (cascade rules) |
| GET | `/rules` | รายการ rules |
| POST | `/rules` | สร้าง rule |
| PATCH | `/rules/{id}` | แก้ไข rule |
| DELETE | `/rules/{id}` | ลบ rule |
| POST | `/rules/{id}/enable` | เปิด rule |
| POST | `/rules/{id}/disable` | ปิด rule |

### Events
| Method | Endpoint | คำอธิบาย |
|---|---|---|
| GET | `/events` | รายการ events พร้อม filter |
| POST | `/events/{id}/acknowledge` | ยืนยัน event |
| POST | `/events/{id}/silence` | ปิดเสียง N วินาที |
| POST | `/events/{id}/escalate` | ส่งต่อ escalation |
| DELETE | `/events/{id}` | ลบ event (ADMIN+) |
| GET | `/events/{id}/clip` | ดาวน์โหลด video clip |
| POST | `/events/purge` | bulk delete ตาม filter + dry_run mode |

### Users
| Method | Endpoint | คำอธิบาย |
|---|---|---|
| GET | `/users` | รายการ users (ADMIN+) |
| POST | `/users` | สร้าง user (ADMIN+) |
| PATCH | `/users/{id}` | แก้ไข user (ADMIN+) |
| DELETE | `/users/{id}` | ลบ user (SUPERADMIN) |
| POST | `/users/me/change-password` | เปลี่ยนรหัสผ่านตัวเอง |

### System Settings
| Method | Endpoint | คำอธิบาย |
|---|---|---|
| GET | `/system/settings` | รายการ settings (ADMIN+) |
| PATCH | `/system/settings` | อัปเดต setting (ADMIN+) |

Settings ที่ปรับได้:
| Key | ประเภท | ค่าที่รับได้ | หมายเหตุ |
|---|---|---|---|
| `jwt_access_token_expire_minutes` | int | 5–1440 | มีผลกับ token ใหม่ |
| `jwt_refresh_token_expire_days` | int | 1–90 | มีผลกับ token ใหม่ |
| `default_cooldown_seconds` | int | 10–600 | มีผลทันที — ห่างเท่าไหร่ก่อน object เดิม trigger ซ้ำ |
| `default_confidence_threshold` | int | 10–95 (%) | มีผลทันที — AI ต้องมั่นใจขั้นต่ำเท่าไหรจึงนับ detection |
| `stream_tier` | str | THUMBNAIL/MONITOR/DETAIL | มีผลทันที (กล้อง restart ~2-3 วิ) |
| `evidence_tier` | str | MONITOR/DETAIL/EVIDENCE | มีผลทันที (กล้อง restart ~2-3 วิ) |
| `clip_crf` | int | 18–28 | มีผลทันที (18=คมที่สุด) |
| `clip_pre_seconds` | int | 2–30 วิ | มีผลทันทีกับ clip ถัดไป |
| `clip_post_seconds` | int | 2–30 วิ | มีผลทันทีกับ clip ถัดไป |

### Other
| Method | Endpoint | คำอธิบาย |
|---|---|---|
| GET | `/health` | สถานะระบบ, CPU, RAM, cameras |
| GET | `/lpr` | LPR plate history |
| POST | `/simulate/alert` | trigger alert จำลอง (debug mode) |
| WS | `/ws?token=JWT` | WebSocket — alert_fired, frame_ready, camera_state |

ดู Swagger UI ที่ `/api/docs` สำหรับ schema ครบถ้วน (debug mode เท่านั้น)

---

## Video Quality Architecture

CameraThread encode ทุก frame เป็น 3 tier แยกกัน:

```
raw frame
  ├─ THUMBNAIL (320×180 q60)  → frame_buffer  → AI Pipeline
  ├─ evidence_tier*           → hires_buffer  → Snapshot + Clip
  └─ stream_tier*             → stream_buffer → MJPEG Live Stream
```

*กำหนดได้โดย Admin ผ่าน Settings → ระบบ

---

## Notification Channels

ตั้งค่าใน `backend\.env`:

```env
LINE_CHANNEL_ACCESS_TOKEN=...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=alerts@yourdomain.com
SMTP_PASSWORD=...
```

---

## Production Deployment (Linux + nginx)

```bash
# 1. Build frontend
cd frontend && npm run build
sudo cp -r dist /var/www/mtsecurity

# 2. ตั้งค่า nginx
sudo cp nginx.conf /etc/nginx/sites-available/mtsecurity
sudo ln -s /etc/nginx/sites-available/mtsecurity /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx

# 3. รัน backend ด้วย uvicorn
cd backend
uvicorn api.app:app --host 0.0.0.0 --port 8000
```

## Production Deployment (Windows + NSSM)

```powershell
# รันในฐานะ Administrator
.\scripts\check-startup.ps1      # ตรวจสอบ environment
.\scripts\install-services.ps1   # ติดตั้ง service
nssm start MTSecurityBackend
nssm start MTSecurityFrontend
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy 2 (async), SQLite/PostgreSQL |
| AI | OpenVINO, YOLOv11n, ByteTrack |
| Video | OpenCV, FFmpeg (clip + faststart) |
| Frontend | Vue 3, TypeScript, Vite, DaisyUI 5, Pinia |
| Real-time | WebSocket (native FastAPI), MJPEG stream |
| Auth | JWT (HS256), Fernet encryption, RBAC + camera scoping |
| Test | pytest-asyncio |
