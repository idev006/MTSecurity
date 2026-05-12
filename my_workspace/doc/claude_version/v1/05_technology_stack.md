# 05 — Technology Stack

> หลักการ: เลือก Technology ด้วยเหตุผล ไม่ใช่ความนิยม
> ทุก choice ระบุ "ทำไมไม่เลือกตัวอื่น" ไว้ด้วย

---

## 1. ภาษาหลัก

### Python 3.11+
**ทำไม:** Ecosystem ที่ครบที่สุดสำหรับ CV/AI — OpenCV, NumPy, Shapely, OpenVINO ล้วน first-class support
**ทำไมไม่ Go/Rust:** Library CV ต้องใช้ Python bindings อยู่ดี, overhead ของ FFI ไม่คุ้มกับ latency ที่เราต้องการ
**ทำไม 3.11 ไม่ใช่ 3.12:** OpenVINO และ PaddleOCR มี binary wheel สำหรับ 3.11 ดีที่สุด ณ เวลาที่เขียนเอกสาร

---

## 2. Computer Vision & AI

### OpenCV 4.x — Video Capture & Image Processing
```
ใช้สำหรับ  : RTSP decode, resize, crop, annotate (bounding box)
ทางเลือกอื่น: FFmpeg + PyAV — decode เร็วกว่าแต่ต้องเขียน pipeline เอง
เหตุผล     : OpenCV ครอบคลุมทุกอย่างในไลบรารีเดียว, community ใหญ่
ข้อระวัง  : OpenCV บน Windows ต้องใช้ DSHOW หรือ MSMF backend
             สำหรับ RTSP ใช้ GStreamer backend จะเสถียรกว่า
```

### OpenVINO 2024.x — AI Inference Runtime
```
ใช้สำหรับ  : รัน YOLOv8 + LPR detector บน CPU (Intel/AMD)
ทำไมไม่ ONNX Runtime : OpenVINO เร็วกว่า 2-3× บน Intel/AMD CPU
                       ด้วย INT8 quantization ซึ่ง ONNX Runtime ทำยากกว่า
ทำไมไม่ TensorRT    : ต้องการ NVIDIA GPU — ไม่มีในระบบนี้
ทำไมไม่ PyTorch     : Inference mode ช้ากว่า OpenVINO ~3× บน CPU
ข้อระวัง  : Model ต้อง export เป็น OpenVINO IR format ก่อนใช้
             YOLOv8 → ultralytics.export(format="openvino", half=True)
```

### YOLOv8n — Object Detection Model
```
ใช้สำหรับ  : ตรวจจับ person, car, motorcycle, truck, bus, bicycle,
             dog, cat, bird (80 COCO classes)
ทำไม nano : nano (n) เพียงพอสำหรับ use case นี้, เร็ว 2× กว่า small
             Accuracy trade-off ยอมรับได้เมื่อ confidence ≥ 0.5
ทำไมไม่ v9/v10: ณ เวลาที่เขียน OpenVINO export pipeline ของ v8 เสถียรกว่า
Model size : ~6MB (INT8) — โหลดครั้งเดียว, วน 10 กล้อง

Performance Target:
  Input 640×640 INT8 → ~40-60ms บน Ryzen 7 5700G (1 thread)
  Input 320×320 INT8 → ~15-25ms (สำหรับ use case ที่ยอม accuracy)
```

### ByteTrack — Multi-Object Tracking
```
ใช้สำหรับ  : กำหนด track_id ให้วัตถุข้ามเฟรม
ทำไมไม่ DeepSORT : DeepSORT ต้องการ Re-ID model แยก (~100ms/frame เพิ่ม)
                   ByteTrack ใช้ IoU matching อย่างเดียว — เร็วกว่า 5×
ทำไมไม่ SORT     : ByteTrack จัดการ low-confidence detection ได้ดีกว่า
                   (second association step)
ข้อจำกัด : Re-ID ข้ามกล้อง ต้องการ embedding model เพิ่มในอนาคต
```

### PaddleOCR — License Plate Reading
```
ใช้สำหรับ  : อ่านตัวอักษรบนป้ายทะเบียน (Thai + English + Numbers)
ทำไมไม่ Tesseract : Tesseract แย่กับ rotated/perspective text
                    PaddleOCR มี built-in text detection + recognition
ทำไมไม่ EasyOCR  : PaddleOCR เร็วกว่าและ accuracy ดีกว่าสำหรับ Thai
ข้อระวัง  : รันเฉพาะ on-demand (เมื่อมี car ใน LPR zone) ไม่ใช่ round-robin
```

---

## 3. Backend Framework

### FastAPI — REST API + WebSocket
```
ใช้สำหรับ  : REST endpoints (CRUD), WebSocket (real-time stream)
ทำไมไม่ Django : Django overkill สำหรับ API-only server, async support รอง
ทำไมไม่ Flask  : Flask ไม่ built-in async + WebSocket ต้องติด extension เพิ่ม
ทำไม FastAPI  : async-first, Pydantic validation built-in,
                 auto-generate OpenAPI docs, WebSocket ง่าย
```

### SQLAlchemy 2.0 (async) — ORM
```
ใช้สำหรับ  : Database operations จาก FastAPI (async)
ทำไมไม่ raw psycopg : SQLAlchemy จัดการ connection pool + migration integration
ทำไมไม่ Tortoise ORM: SQLAlchemy ecosystem ใหญ่กว่า, mature มากกว่า
```

### Alembic — Database Migration
```
ใช้สำหรับ  : Version control ของ schema เปลี่ยนแปลง
เหตุผล    : integrate กับ SQLAlchemy โดยตรง, industry standard
```

---

## 4. Data Storage

### Database Strategy — SQLite → PostgreSQL Migration Path

```
Phase 1 (ปัจจุบัน) : SQLite 3
Phase 2 (Production): PostgreSQL 15

เปลี่ยนได้ด้วยการแก้ DATABASE_URL เพียง 1 บรรทัด
SQLAlchemy ORM เป็น abstraction layer — SQL ไม่ต้องแก้
```

### SQLite 3 — Initial Database (Phase 1)
```
ใช้สำหรับ  : ทุก table เหมือน PostgreSQL ผ่าน SQLAlchemy ORM
ข้อดี     : ไม่ต้อง install server, ไฟล์เดียว, deploy ง่าย, ทดสอบเร็ว
ข้อจำกัด : concurrent writer ได้แค่ 1 ในเวลาเดียว (ใช้ WAL mode แก้ได้)

การตั้งค่าบังคับ (PRAGMA สำคัญ):
  PRAGMA journal_mode = WAL;     ← reader ไม่ block writer
  PRAGMA foreign_keys = ON;      ← enforce FK constraint
  PRAGMA synchronous = NORMAL;   ← balance ระหว่าง safety/speed
  PRAGMA busy_timeout = 5000;    ← รอ 5s ก่อน throw "database is locked"

Driver:
  sync  → sqlite3 (built-in)
  async → aiosqlite
```

### PostgreSQL 15 — Production Database (Phase 2)
```
เปลี่ยนเมื่อ: กล้อง > 10 ตัว, concurrent user > 5, หรือต้องการ JSONB index
ข้อดี      : MVCC (ไม่ lock), JSONB index, pg_partitioning สำหรับ events table
เปลี่ยนวิธี: แก้ DATABASE_URL + run alembic migrate → จบ
```

### Database URL Pattern (ใน .env)
```bash
# Phase 1 — SQLite
DATABASE_URL=sqlite+aiosqlite:///./data/mtsecurity.db

# Phase 2 — PostgreSQL (เปลี่ยนบรรทัดนี้อย่างเดียว)
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/mtsecurity
```

### SQLite-specific Type Mapping (SQLAlchemy)
```
PostgreSQL type    → SQLAlchemy type      → SQLite storage
─────────────────────────────────────────────────────────
BIGSERIAL          → BigInteger (AI=True) → INTEGER
TIMESTAMPTZ        → DateTime(tz=True)    → TEXT (ISO8601)
JSONB              → JSON                 → TEXT
TEXT[]             → JSON                 → TEXT  ← สำคัญ! ไม่มี Array type
VARCHAR(n)         → String(n)            → TEXT
BOOLEAN            → Boolean              → INTEGER (0/1)
REAL               → Float               → REAL
```

### Redis 7 — Cache & Pub/Sub
```
ใช้สำหรับ  : Alert cooldown storage (SETEX), session cache
ทำไมไม่ in-memory dict : dict ไม่ shared ระหว่าง process,
                          ถ้า process restart — cooldown หาย
ทำไม Redis  : SETEX คือ atomic TTL-based expiry, persist ได้,
               ถ้าต้องการ horizontal scale ใน future ใช้ Redis Cluster

Phase 1 alternative: ถ้าไม่อยากติดตั้ง Redis ในช่วงแรก
  ใช้ TTLCache (cachetools) in-memory แทนได้ชั่วคราว
  แต่ต้อง refactor ก่อน production
```

---

## 5. Infrastructure

### Docker + Docker Compose — Containerization
```
ใช้สำหรับ  : package ทุก service ให้ reproducible
ทำไม Compose : ระบบนี้รันบน single host — K8s overkill
เหตุผล     : isolate dependencies, restart policy, resource limits
```

### Nginx — Reverse Proxy
```
ใช้สำหรับ  : SSL termination, WebSocket proxy, static file serving
ทำไม Nginx  : เร็ว, ดูแลง่าย, WebSocket upgrade built-in
config ที่สำคัญ:
  proxy_read_timeout 86400;   ← keep WebSocket alive
  proxy_buffering off;         ← ไม่ buffer stream
```

---

## 6. Frontend

### React + TypeScript — Web Dashboard
```
ใช้สำหรับ  : Real-time video feed, Zone editor, Event log, Analytics
ทำไม React  : Component-based ดีกับ Dashboard ที่มีหลาย panel
ทำไม TS    : Type safety ลด bug จาก API contract ไม่ตรง

Key Libraries:
  - Konva.js  : วาด Polygon บนภาพ (Zone Editor)
  - Recharts  : กราฟ Analytics
  - Socket.IO : WebSocket client
```

---

## 7. Notification Services

### LINE Messaging API (ไม่ใช่ LINE Notify)
```
เหตุผล    : LINE Notify deprecated 2025-03-31
            ใช้ LINE Messaging API แทน
ต้องการ  : LINE Developer Account + Bot Channel
วิธีส่ง  : POST /v2/bot/message/push พร้อม flex message + image
```

### SMTP Email — smtplib + jinja2
```
ใช้สำหรับ  : Alert summary, Daily report
ทำไมไม่ SendGrid : ไม่ต้องการ third-party สำหรับ basic email
                   ใช้ Gmail SMTP + App Password ก็ได้
```

### MQTT via paho-mqtt
```
ใช้สำหรับ  : ส่ง trigger ไปยัง IoT device (ไซเรน, relay, สปอตไลท์)
Protocol  : MQTT 3.1.1, QoS 1
Topic     : mtsecurity/alerts/{camera_id}/{event_type}
```

---

## 8. Dependency Summary

```toml
# pyproject.toml (สรุป)
[tool.poetry.dependencies]
python          = "^3.11"

# Vision & AI
opencv-python   = "^4.9"
openvino        = "^2024.1"
ultralytics     = "^8.2"          # สำหรับ export model เท่านั้น
paddlepaddle    = "^2.6"
paddleocr       = "^2.7"

# Tracking
numpy           = "^1.26"
scipy           = "^1.13"
lap             = "^0.4"          # ByteTrack dependency

# Geometry
shapely         = "^2.0"

# Backend
fastapi         = "^0.111"
uvicorn         = {extras=["standard"], version="^0.29"}
sqlalchemy      = "^2.0"
alembic         = "^1.13"

# Database drivers  ← เลือกตาม phase
aiosqlite       = "^0.20"         # Phase 1: SQLite async driver
asyncpg         = "^0.29"         # Phase 2: PostgreSQL async driver (เพิ่มเมื่อ migrate)

# Cache
redis           = "^5.0"
cachetools      = "^5.3"          # fallback TTLCache ถ้ายังไม่มี Redis

# Notifications
httpx           = "^0.27"         # LINE API + Webhook
paho-mqtt       = "^1.6"
Pillow          = "^10.3"         # Snapshot annotation
jinja2          = "^3.1"          # Email template

# Config & Validation
pydantic-settings = "^2.2"
python-dotenv   = "^1.0"

[tool.poetry.group.dev.dependencies]
pytest          = "^8.2"
pytest-asyncio  = "^0.23"
httpx           = "^0.27"         # TestClient
factory-boy     = "^3.3"
```

---

## 9. Performance Benchmark (เป้าหมายที่ต้องทดสอบ)

```
Hardware: Ryzen 7 5700G, 16GB DDR4, No GPU

Test: 10 กล้อง RTSP 1080p, YOLOv8n INT8, ByteTrack

Target metrics:
  Inference latency (P50)  : < 60ms
  Inference latency (P95)  : < 100ms
  Effective FPS per camera : ≥ 1.0 FPS
  Total RAM (all services) : < 8 GB
  CPU utilization          : < 70% average
  Alert end-to-end latency : < 3 seconds (P95)

Tuning knobs:
  - fps_target per camera (default 5, min 1)
  - inference_input_size (320 หรือ 640)
  - max_cameras_active (ปิดกล้องที่ offline อัตโนมัติ)
```
