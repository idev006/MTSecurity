# MTSecurity v2 — Deployment Guide

> เอกสารนี้ครอบคลุมทุก deployment scenario ตั้งแต่ dev ถึง production

---

## สารบัญ

1. [Prerequisites](#1-prerequisites)
2. [Development (Docker Compose)](#2-development-docker-compose) ← **แนะนำสำหรับ dev**
3. [Development (Native / no Docker)](#3-development-native)
4. [Production (Docker Compose)](#4-production-docker-compose)
5. [Production (Linux + systemd)](#5-production-linux--systemd)
6. [Secrets Management](#6-secrets-management)
7. [AI Model Setup](#7-ai-model-setup)
8. [First-run Admin Account](#8-first-run-admin-account)
9. [Troubleshooting](#9-troubleshooting)

---

## 1. Prerequisites

### Docker path (recommended)
| Software | Min Version | Install |
|----------|------------|---------|
| Docker Desktop | 26+ | https://docs.docker.com/get-docker/ |
| Docker Compose | v2 (bundled) | included with Docker Desktop |

### Native path
| Software | Min Version | Install |
|----------|------------|---------|
| Python | 3.11+ | https://python.org |
| Node.js | 20+ | https://nodejs.org |
| FFmpeg | 6+ | https://ffmpeg.org |

---

## 2. Development (Docker Compose)

**นี่คือ workflow หลักสำหรับการพัฒนา**

### 2.1 ครั้งแรก — Setup

```bash
# 1. Clone repository
git clone https://github.com/idev006/MTSecurity.git
cd MTSecurity/my_workspace

# 2. ตั้งค่า root secrets (postgres, grafana)
cp .env.example .env    # หรือใช้ .env ที่มีอยู่แล้ว
# แก้ไข .env:
#   POSTGRES_PASSWORD=your_secure_password
#   GF_SECURITY_ADMIN_PASSWORD=your_grafana_password

# 3. ตั้งค่า backend secrets
cp backend/.env.docker.example backend/.env.docker   # ถ้ามี
# แก้ไข backend/.env.docker:
#   JWT_SECRET_KEY=<สุ่ม 32 bytes>
#   ENCRYPTION_KEY=<Fernet key>

# 4. Build images (ทำแค่ครั้งแรก หรือเมื่อ Dockerfile เปลี่ยน)
docker compose build

# 5. Start stack
docker compose up -d
```

### 2.2 การใช้งานประจำวัน

```bash
# ⚠️  ระบบยังไม่นิ่ง — ยังไม่ควร rebuild images ทุกครั้ง
# ใช้ up โดยไม่มี --build เพื่อ start containers ที่ build ไว้แล้ว

# Start all containers (ไม่ rebuild)
docker compose up -d

# Stop all containers
docker compose down

# Restart specific service (เช่นหลังแก้ code backend)
docker compose restart backend

# ดู logs
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f   # ทุก service พร้อมกัน

# ดูสถานะ
docker compose ps
```

> **หมายเหตุสำคัญ:**
> - `docker compose up --build` ใช้เฉพาะเมื่อ **Dockerfile หรือ package.json/requirements.txt เปลี่ยน**
> - โค้ด Python/Vue ใน volume mount จะ hot-reload อัตโนมัติ ไม่ต้อง rebuild
> - Backend: uvicorn รันอยู่ใน container, reload ทุกครั้งที่ `.py` เปลี่ยน
> - Frontend: Vite dev server รันอยู่ ที่ port 5173, HMR ทำงานอัตโนมัติ

### 2.3 Rebuild (เฉพาะเมื่อจำเป็น)

```bash
# Rebuild เฉพาะ service ที่เปลี่ยน dependencies
docker compose build backend    # เมื่อ requirements.txt เปลี่ยน
docker compose build frontend   # เมื่อ package.json เปลี่ยน

# แล้วค่อย recreate container นั้น
docker compose up -d backend
docker compose up -d frontend
```

### 2.4 Access URLs (Development)

| Service | URL | หมายเหตุ |
|---------|-----|---------|
| **App (หลัก)** | http://localhost | ผ่าน nginx |
| **Frontend (Vite)** | http://localhost:5173 | direct dev server |
| **API Docs** | http://localhost/api/docs | Swagger (DEBUG mode เท่านั้น) |
| **Grafana** | http://localhost:3000 | admin / (ตาม .env) |
| **PostgreSQL** | localhost:5432 | mtsecurity / (ตาม .env) |
| **Redis** | localhost:6379 | ไม่ต้องการ password |

---

## 3. Development (Native / ไม่ใช้ Docker)

ใช้สำหรับ debug หรือเครื่องที่ไม่มี Docker

### 3.1 Backend

```bash
# สร้าง virtual environment
python -m venv D:\dev\MTSecurity\my_env
D:\dev\MTSecurity\my_env\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt

# ตั้งค่า env
copy .env.example .env
# แก้ไข .env ด้วย JWT_SECRET_KEY, ENCRYPTION_KEY, FFMPEG_PATH

# สร้าง keys
python -c "import secrets; print(secrets.token_hex(32))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Start backend
python main.py --reload    # dev mode
python main.py             # normal mode
```

### 3.2 Frontend

```bash
cd frontend
npm install
copy .env.example .env   # VITE_BACKEND_URL=http://localhost:8000

npm run dev    # dev server → http://localhost:5173
npm run build  # production build → dist/
```

### 3.3 Native URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| API Docs | http://localhost:8000/api/docs |

---

## 4. Production (Docker Compose)

### 4.1 Setup Production

```bash
# ใช้เฉพาะ docker-compose.yml (ไม่ใช้ override)
docker compose -f docker-compose.yml up -d --build
```

### 4.2 Differences vs Development

| Aspect | Development | Production |
|--------|-------------|-----------|
| Frontend | Vite dev server (port 5173) | nginx static (port 80) |
| Backend | code in volume mount | code baked into image |
| Memory | backend 8g, frontend 1g | backend 2g, frontend 64m |
| Ports | postgres:5432, redis:6379 exposed | internal only |
| Nginx config | mtsecurity.dev.conf (→5173) | mtsecurity.conf (→80) |

### 4.3 Production .env

```env
# my_workspace/.env
POSTGRES_DB=mtsecurity
POSTGRES_USER=mtsecurity
POSTGRES_PASSWORD=<strong_password_min_20chars>

GF_SECURITY_ADMIN_PASSWORD=<strong_password>
```

### 4.4 Production backend/.env.docker

```env
ENVIRONMENT=production
DEBUG=false

DATABASE_URL=postgresql+asyncpg://mtsecurity:<password>@postgres:5432/mtsecurity
REDIS_URL=redis://redis:6379/0

JWT_SECRET_KEY=<64 hex chars — python: secrets.token_hex(32)>
ENCRYPTION_KEY=<Fernet key — python: Fernet.generate_key().decode()>

# Notifications (optional)
LINE_CHANNEL_ACCESS_TOKEN=
DISCORD_WEBHOOK_URL=
SLACK_WEBHOOK_URL=

CORS_ORIGINS=https://your-domain.com
BASE_URL=https://your-domain.com
```

### 4.5 Update Production

```bash
git pull origin main

# rebuild only changed services
docker compose -f docker-compose.yml build backend frontend

# rolling restart (backend first, nginx last)
docker compose -f docker-compose.yml up -d backend
docker compose -f docker-compose.yml up -d frontend nginx
```

---

## 5. Production (Linux + systemd)

สำหรับ deployment บน VPS หรือ bare metal โดยไม่ใช้ Docker

```bash
# Backend service: /etc/systemd/system/mtsecurity-backend.service
[Unit]
Description=MTSecurity Backend
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=mtsecurity
WorkingDirectory=/opt/mtsecurity/backend
ExecStart=/opt/mtsecurity/venv/bin/python main.py
Restart=always
RestartSec=5
EnvironmentFile=/opt/mtsecurity/backend/.env

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable mtsecurity-backend
systemctl start mtsecurity-backend
systemctl status mtsecurity-backend
```

---

## 6. Secrets Management

### Generate Keys

```bash
# JWT Secret Key (min 32 bytes random)
python -c "import secrets; print(secrets.token_hex(32))"

# Fernet Encryption Key (for RTSP URL encryption)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### ⚠️ Security Rules

```
1. ห้าม commit .env ที่มี secrets จริงเข้า git
2. ใช้ .env.example หรือ .env.docker.example สำหรับ template
3. ใน production: ใช้ Docker Secrets หรือ Vault แทน environment variables
4. Rotate JWT_SECRET_KEY ทำให้ tokens ทุกตัวหมดอายุ (log out ทุกคน)
5. Rotate ENCRYPTION_KEY ต้อง re-encrypt RTSP URLs ทุกตัวในฐานข้อมูล
```

### ⚠️ Current Known Issue

> ไฟล์ `.env` และ `backend/.env.docker` ที่มี secrets จริงถูก commit เข้า git แล้ว  
> ต้อง rotate secrets ก่อน deploy production:  
> 1. Generate keys ใหม่  
> 2. Update ไฟล์ .env  
> 3. Force-push หรือ git history cleanup

---

## 7. AI Model Setup

### Download YOLO11n OpenVINO Model

```bash
# Install downloader
pip install openvino-dev

# Download (backend/scripts/download_model.py)
cd backend
python scripts/download_model.py

# หรือ manual download:
# 1. Export from Ultralytics:
pip install ultralytics
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt').export(format='openvino')"

# 2. Copy ไฟล์
#    yolo11n_openvino_model/yolo11n.xml
#    yolo11n_openvino_model/yolo11n.bin
# ไปไว้ที่:
#    backend/data/models/yolo11n.xml
#    backend/data/models/yolo11n.bin
```

### Docker Volume Mount

โมเดลถูก mount ผ่าน named volume `models:/app/data/models`  
วิธี copy ไฟล์เข้า volume:

```bash
# Method 1: ผ่าน container
docker cp backend/data/models/yolo11n.xml mtsecurity-backend-1:/app/data/models/
docker cp backend/data/models/yolo11n.bin mtsecurity-backend-1:/app/data/models/

# Method 2: Mount local directory ใน override (dev เท่านั้น)
# ใน docker-compose.override.yml:
#   volumes:
#     - ./backend/data/models:/app/data/models
```

> **หมายเหตุ:** ถ้าไม่มีโมเดล ระบบ start ได้ แต่ AI Pipeline จะ disable  
> กล้องยังดูสดได้ แต่จะไม่มี detection/alert

---

## 8. First-run Admin Account

เมื่อรันครั้งแรก ไม่มี user ในฐานข้อมูล

```bash
# สร้าง SUPERADMIN account

# Docker (recommended)
docker exec -it mtsecurity-backend-1 python scripts/create_admin.py

# Native
cd backend
python scripts/create_admin.py
```

Script จะถาม username, email, password  
จากนั้น login ที่ http://localhost (หรือ port ที่ตั้งไว้)

---

## 9. Troubleshooting

### Services ไม่ start

```bash
# ดู logs ทุก service
docker compose logs --tail=50

# ดูเฉพาะ service ที่มีปัญหา
docker compose logs backend --tail=50
docker compose logs postgres --tail=20
```

### Backend: database connection error

```bash
# ตรวจสอบ postgres ว่า healthy
docker compose ps postgres

# ดู postgres logs
docker compose logs postgres

# ตรวจสอบ DATABASE_URL ใน .env.docker
# ต้องเป็น: postgresql+asyncpg://mtsecurity:PASSWORD@postgres:5432/mtsecurity
```

### Frontend: blank page / 502

```bash
# ตรวจสอบ frontend status
docker compose logs frontend --tail=20

# ตรวจสอบว่า Vite start แล้ว (ดู "VITE vX ready")
docker compose logs frontend | grep "ready"

# ถ้ายัง starting: รอ 10-15 วินาที แล้วลอง refresh
```

### Port already in use

```bash
# หยุด process ที่ใช้ port 80
# Windows:
netstat -ano | findstr :80
taskkill /PID <PID> /F

# Linux:
sudo fuser -k 80/tcp
```

### Rebuild เมื่อไม่จำเป็น (ช้า)

```bash
# ❌ อย่าทำนี้ทุกครั้ง
docker compose up --build -d

# ✅ ทำแค่นี้ถ้าโค้ดเปลี่ยน (volume mount reload อัตโนมัติ)
docker compose up -d

# ✅ Rebuild เฉพาะถ้า dependencies เปลี่ยน
docker compose build backend   # requirements.txt เปลี่ยน
docker compose build frontend  # package.json เปลี่ยน
docker compose up -d
```

### ล้างข้อมูลทั้งหมด (Nuclear reset)

```bash
# ⚠️ ลบ volumes ทั้งหมด รวมถึง database
docker compose down -v

# จากนั้น start ใหม่
docker compose up -d
```

### ดู resource usage

```bash
docker stats
docker compose top
```

### เข้า container โดยตรง

```bash
docker exec -it mtsecurity-backend-1 bash
docker exec -it mtsecurity-postgres-1 psql -U mtsecurity mtsecurity
docker exec -it mtsecurity-redis-1 redis-cli
```

---

## Appendix: Environment Variables Reference

### root `.env`
| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_DB` | ✅ | Database name (default: mtsecurity) |
| `POSTGRES_USER` | ✅ | DB username |
| `POSTGRES_PASSWORD` | ✅ | DB password |
| `GF_SECURITY_ADMIN_PASSWORD` | ✅ | Grafana admin password |

### `backend/.env.docker`
| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_SECRET_KEY` | ✅ | HS256 signing key (32+ random bytes) |
| `ENCRYPTION_KEY` | ✅ | Fernet key for RTSP URL encryption |
| `DATABASE_URL` | ✅ | Async SQLAlchemy URL |
| `REDIS_URL` | ✅ | Redis connection URL |
| `ENVIRONMENT` | | production / development |
| `DEBUG` | | true / false (enables /api/docs) |
| `MODEL_PATH` | | Path to YOLO XML file |
| `MODEL_DEVICE` | | CPU / GPU / AUTO |
| `AI_CONFIDENCE_THRESHOLD` | | 0.0–1.0 (default: 0.6) |
| `LINE_CHANNEL_ACCESS_TOKEN` | | LINE Messaging API |
| `DISCORD_WEBHOOK_URL` | | Discord webhook |
| `SLACK_WEBHOOK_URL` | | Slack incoming webhook |
| `CORS_ORIGINS` | | Allowed CORS origins |
| `RATE_LIMIT_LOGIN` | | e.g. `5/minute` |
| `RATE_LIMIT_API` | | e.g. `200/minute` |
