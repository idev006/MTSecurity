# MTSecurity v2 — Pilot's Console

ระบบกล้องวงจรปิดอัจฉริยะพร้อม AI Detection, Real-time Alerts, และ Cockpit UI

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
| OpenCV-Python | (auto via pip) | — |

---

## Setup (ครั้งแรกเท่านั้น)

### 1. Backend

```bat
:: สร้าง virtualenv (ทำครั้งเดียว — ใช้ร่วมกันทั้งโปรเจกต์)
python -m venv D:\dev\MTSecurity\my_env
D:\dev\MTSecurity\my_env\Scripts\pip install -r my_workspace\backend\requirements.txt

:: ตั้งค่า env
copy my_workspace\backend\.env.example my_workspace\backend\.env
```

แก้ไข `backend\.env`:
```env
JWT_SECRET_KEY=สุ่มอย่างน้อย 32 ตัวอักษร
ENCRYPTION_KEY=สร้างด้วย Fernet.generate_key()
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
| API Docs | http://localhost:8000/docs | Swagger UI |
| WebSocket | ws://localhost:8000/api/v1/ws | Real-time events |

---

## โครงสร้างโปรเจกต์

```
my_workspace/
├── backend/                    FastAPI + Python
│   ├── api/                    REST routers + WebSocket hub
│   │   ├── routers/            auth, cameras, zones, rules, events, users, health
│   │   └── websocket/          hub.py, router.py
│   ├── ai/                     OpenVINO inference, detector, tracker, pipeline
│   ├── alerts/                 snapshot, notifications (LINE/Discord/Slack/SMTP/MQTT/Webhook)
│   ├── auth/                   JWT handler, password hash, RBAC permissions
│   ├── db/                     SQLAlchemy session, migrations, init
│   ├── ingestion/              CameraThread (RTSP + Webcam), CameraManager, FrameBuffer
│   ├── models/                 ORM models (Camera, Zone, Rule, Event, User, …)
│   ├── protocol/               MessageBus (MTP), payloads
│   ├── rules/                  RuleEngine, ZoneManager, DwellTracker, behaviors
│   ├── schemas/                Pydantic v2 request/response schemas
│   ├── ssot/                   StateRegistry, ConfigService
│   ├── tests/                  unit/ + integration/ (182 tests)
│   ├── config.py               Settings (pydantic-settings, reads .env)
│   ├── main.py                 Boot orchestrator
│   ├── .env.example            Template env vars
│   └── requirements.txt
│
├── frontend/                   Vue 3 + TypeScript + DaisyUI 5
│   ├── src/
│   │   ├── api/                client.ts — typed API wrappers (relative paths)
│   │   ├── components/         AppLayout.vue (navbar + sidebar + statusbar)
│   │   ├── router/             index.ts — auth guards
│   │   ├── stores/             auth, cameras, events, system (Pinia)
│   │   └── views/              Login, Dashboard, Cameras, Events, Settings
│   ├── .env.example
│   └── vite.config.ts          Proxy /api → backend
│
├── scripts/
│   ├── install-services.ps1    ติดตั้ง NSSM Windows Service
│   └── check-startup.ps1       ตรวจสอบ environment ก่อนเริ่ม
│
├── doc/                        เอกสาร Architecture (v1, v2)
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

---

## Roles & Permissions

| Role | สิทธิ์ |
|---|---|
| `SUPERADMIN` | ทุกอย่าง รวมถึงลบกล้อง, จัดการ users |
| `ADMIN` | จัดการกล้อง, zones, rules, events |
| `OPERATOR` | ดูกล้องที่ได้รับมอบหมาย, ยืนยัน events |
| `VIEWER` | ดูอย่างเดียว |

---

## API Overview

Base path: `/api/v1/`

| Method | Endpoint | คำอธิบาย |
|---|---|---|
| POST | `/auth/login` | รับ access + refresh token |
| POST | `/auth/logout` | revoke token |
| POST | `/auth/refresh` | ต่ออายุ token |
| GET | `/auth/me` | ข้อมูล user ปัจจุบัน |
| GET | `/cameras` | รายการกล้องทั้งหมด |
| POST | `/cameras` | เพิ่มกล้อง (RTSP หรือ Webcam) |
| PATCH | `/cameras/{id}` | แก้ไข / enable / disable กล้อง |
| DELETE | `/cameras/{id}` | ลบกล้อง (SUPERADMIN) |
| GET | `/cameras/{id}/status` | สถานะ runtime (FPS, latency, state) |
| GET | `/cameras/webcams` | scan USB webcam ที่เชื่อมต่ออยู่ (index 0-9) |
| GET | `/events` | รายการ events พร้อม filter |
| POST | `/events/{id}/acknowledge` | ยืนยัน event |
| POST | `/events/{id}/silence` | ปิดเสียง N วินาที |
| POST | `/events/{id}/escalate` | ส่งต่อ escalation |
| GET | `/health` | สถานะระบบ, CPU, RAM, cameras |
| WS | `/api/v1/ws?token=JWT` | WebSocket — alert_fired, frame_ready |

ดู Swagger UI ที่ `/docs` สำหรับ schema ครบถ้วน

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

# 3. รัน backend ด้วย systemd หรือ supervisor
cd backend && python main.py
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
| Backend | Python 3.11, FastAPI, SQLAlchemy 2, SQLite/PostgreSQL |
| AI | OpenVINO, YOLOv11, ByteTrack |
| Frontend | Vue 3, TypeScript, Vite, DaisyUI 5, Pinia |
| Real-time | WebSocket (native FastAPI) |
| Auth | JWT (HS256), Fernet encryption, RBAC |
| Test | pytest-asyncio (182 tests) |
