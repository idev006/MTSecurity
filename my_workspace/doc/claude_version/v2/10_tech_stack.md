# 10 — Tech Stack & Architecture Decisions
### Technology Choices · Dependencies · Hardware Profile · ADR

---

## 0. Project Paths (Confirmed)

```
Virtual Environment : D:\dev\MTSecurity\my_env\
                      Python 3.12.10 ✅ (confirmed)
Project Root        : D:\dev\MTSecurity\my_workspace\
Documentation       : D:\dev\MTSecurity\my_workspace\doc\claude_version\v2\

Pre-installed in venv:
  numpy              2.4.4    ✅
  openvino           2026.1.0 ✅  ← ใช้แทน ONNX Runtime (ADR-04)
  openvino-telemetry 2025.2.0 ✅
```

---

## 1. Cross-Platform OS Support

### Supported Platforms

```
OS              Version           Status
──────────────────────────────────────────────────────
Windows         10 / 11 (64-bit) ✅ Primary dev environment
Linux           Ubuntu 22.04+    ✅ Recommended production
                Debian 12+
macOS           12 Monterey+     ✅ Development supported
```

### Stack ที่รองรับทุก OS

```
Python 3.12     ✅ cross-platform
OpenVINO 2026   ✅ Windows / Linux / macOS (Intel + AMD)
OpenCV 4.9      ✅ ทุก OS
FastAPI         ✅ ทุก OS (ASGI/asyncio)
Vue 3 + Vite    ✅ ทุก OS (Node.js)
Playwright      ✅ Windows / Linux / macOS
```

### Cross-Platform Coding Rules

```python
# ❌ ห้ามใช้ string path — Windows/Linux separator ต่างกัน
snapshot_dir = "data\\snapshots\\" + filename      # Windows only
snapshot_dir = "data/snapshots/" + filename        # Unix only

# ✅ ใช้ pathlib.Path เสมอ — รองรับทุก OS อัตโนมัติ
from pathlib import Path
snapshot_dir = Path("data") / "snapshots" / filename
# Windows → data\snapshots\filename
# Linux   → data/snapshots/filename

# ✅ Environment paths
from pathlib import Path
BASE_DIR = Path(__file__).parent.resolve()         # absolute path
DATA_DIR = BASE_DIR / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
MODEL_PATH = DATA_DIR / "models" / "yolo11n.xml"  # OpenVINO IR
```

### Service Management per OS

```
Windows  → NSSM (Non-Sucking Service Manager)      ← ดู 13_state_machines.md
Linux    → systemd                                  ← ดู 13_state_machines.md
macOS    → launchd                                  ← ดู 13_state_machines.md
Dev      → uvicorn --reload (ทุก OS)
```

---

## 2. Architecture Pattern

```
Pattern    : Modular Monolith — Event-Driven, OSI-Inspired Layered
Deployment : Single Host (ไม่ใช่ Microservices)
Rationale  : ระบบ 10 กล้อง บน 1 เครื่อง — Microservices เพิ่ม overhead
             โดยไม่ได้ประโยชน์ ทั้ง network latency, deployment complexity
             Modular Monolith ให้ loose coupling แบบเดียวกัน แต่ง่ายกว่า

เปลี่ยนเป็น Microservices ได้ทีหลัง: แต่ละ Tier ใน 01_architecture_manifesto.md
แยก deploy ได้อิสระ เพราะสื่อสารผ่าน MTP/API เท่านั้น
```

---

## 2. Tech Stack ทั้งหมด

### Backend Core

| Technology | Version | ทำไมถึงเลือก |
|---|---|---|
| **Python** | **3.12.10** (fixed) | asyncio native, match statement, PEP 695 type aliases |
| FastAPI | ≥ 0.111 | async-first, Pydantic v2 built-in, auto OpenAPI |
| Pydantic v2 | ≥ 2.7 | validation เร็วกว่า v1 ถึง 17x, model_config syntax ใหม่ |
| SQLAlchemy | ≥ 2.0 | async ORM, type-safe mapped_column, DB-agnostic |
| Alembic | ≥ 1.13 | migration tool คู่กับ SQLAlchemy |
| uvicorn | ≥ 0.29 | ASGI server สำหรับ FastAPI |

### Database

| Technology | ใช้สำหรับ | หมายเหตุ |
|---|---|---|
| SQLite (WAL mode) | Development + Production เริ่มต้น | ไม่ต้องติดตั้ง server, รองรับ concurrent read |
| PostgreSQL | Production เมื่อข้อมูลโต | migrate ได้ไม่ต้องแก้ code (SQLAlchemy abstract) |
| ❌ Redis | ~~Cooldown cache, Token blacklist~~ | **ไม่ใช้** — แทนด้วย TTLCache + DB (ดู ADR-03) |

### AI / Computer Vision

| Technology | Version | ทำไมถึงเลือก |
|---|---|---|
| OpenCV | ≥ 4.9 | RTSP capture, motion detection, frame processing |
| **OpenVINO** | **2026.1.0** (pre-installed ✅) | inference บน CPU เร็วมาก, รองรับ AMD Ryzen (ADR-04) |
| numpy | **2.4.4** (pre-installed ✅) | array operations คู่กับ OpenVINO |
| YOLOv11n | — | โมเดลเล็กที่สุด เหมาะ CPU-only, export เป็น OpenVINO IR |
| ByteTrack | — | object tracking แม่นยำ, open source |
| PaddleOCR | ≥ 2.7 | LPR/OCR บน CPU ได้ ไม่ต้องการ GPU |

> **เปลี่ยนจาก ONNX Runtime → OpenVINO**: เพราะ OpenVINO 2026.1.0 ติดตั้งไว้แล้ว
> และรองรับ AMD Ryzen ได้ดีตั้งแต่ OpenVINO 2023+ (ไม่ใช่ Intel-only อีกต่อไป)

### Authentication & Security

| Technology | ทำไมถึงเลือก |
|---|---|
| python-jose | JWT encode/decode, รองรับ HS256 และ RS256 |
| passlib + bcrypt | password hashing มาตรฐาน, cost factor ปรับได้ |
| cryptography (Fernet) | AES-256-GCM สำหรับ RTSP URL encryption |
| slowapi | rate limiting สำหรับ FastAPI |

### Notification

| Technology | ใช้สำหรับ |
|---|---|
| LINE Messaging API (httpx) | แจ้งเตือนหลัก — คนไทยใช้ LINE |
| SMTP (aiosmtplib) | email backup |
| httpx (async) | webhook sender |
| paho-mqtt | IoT relay (ประตูอัตโนมัติ, etc.) |

### In-Process Cache (แทน Redis)

| Technology | ใช้สำหรับ |
|---|---|
| `cachetools.TTLCache` | alert cooldown (ไม่ส่งซ้ำในช่วง cooldown) |
| DB table `revoked_tokens` | JWT blacklist เมื่อ logout |

### Frontend (Pilot's Console)

| Technology | Version | ทำไมถึงเลือก |
|---|---|---|
| **Vue.js** | **latest (v3)** | Composition API, เบากว่า React, SFC ชัดเจน |
| **TypeScript** | latest | type safety, IDE support ดี |
| **DaisyUI** | **latest** | component library บน Tailwind — ทำ UI เร็ว, theme ได้ |
| Tailwind CSS | ≥ 4.0 | utility-first (DaisyUI ต้องการ Tailwind) |
| Vite | latest | build tool เร็ว, HMR instant |
| Pinia | latest | Vue official state management |
| Vue Router | v4 | routing สำหรับ SPA |

### Testing

| Technology | ใช้สำหรับ |
|---|---|
| pytest | Backend unit + integration test runner |
| pytest-asyncio | test async functions |
| httpx (AsyncClient) | test FastAPI endpoints |
| aiosqlite | in-memory DB สำหรับ test |
| pytest-cov | coverage report |
| **Playwright** | **E2E test + AI-assisted UI testing** |
| Vitest | Frontend unit test (Vue components) |

---

## 3. pyproject.toml

```toml
[project]
name = "mtsecurity"
version = "0.1.0"
requires-python = "==3.12.*"

dependencies = [
    # Web
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.3.0",

    # Database
    "sqlalchemy>=2.0.30",
    "alembic>=1.13.0",
    "aiosqlite>=0.20.0",
    "asyncpg>=0.29.0",

    # Auth & Security
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "cryptography>=42.0.0",
    "slowapi>=0.1.9",

    # AI / CV (openvino + numpy pre-installed in venv)
    "opencv-python-headless>=4.9.0",
    "openvino>=2026.1.0",           # pre-installed ✅
    "numpy>=2.4.4",                 # pre-installed ✅
    "ultralytics>=8.2.0",           # YOLOv11 + export to OpenVINO IR
    "paddlepaddle>=2.6.0",
    "paddleocr>=2.7.0",

    # Cache
    "cachetools>=5.3.0",

    # HTTP client
    "httpx>=0.27.0",

    # MQTT + Email
    "paho-mqtt>=2.0.0",
    "aiosmtplib>=3.0.0",
    "jinja2>=3.1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "playwright>=1.44.0",       # E2E + AI-assisted testing
    "ruff>=0.4.0",
    "mypy>=1.10.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"
select = ["E", "F", "I", "UP", "B", "SIM"]

[tool.mypy]
python_version = "3.12"
strict = true
```

---

## 4. Frontend — package.json

```json
{
  "name": "mtsecurity-console",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev":     "vite",
    "build":   "vue-tsc && vite build",
    "preview": "vite preview",
    "test":    "vitest",
    "e2e":     "playwright test",
    "lint":    "eslint . --ext .vue,.ts"
  },
  "dependencies": {
    "vue":                "^3.5.0",
    "vue-router":         "^4.4.0",
    "pinia":              "^2.2.0",
    "@vueuse/core":       "^11.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite":               "^6.0.0",
    "typescript":         "^5.6.0",
    "vue-tsc":            "^2.1.0",
    "tailwindcss":        "^4.0.0",
    "daisyui":            "^5.0.0",
    "@playwright/test":   "^1.44.0",
    "vitest":             "^2.0.0",
    "@vue/test-utils":    "^2.4.0",
    "eslint":             "^9.0.0",
    "@vue/eslint-config-typescript": "^14.0.0"
  }
}
```

---

## 5. Hardware Requirements

### Minimum (Development / Testing)

```
CPU  : Intel Core i5 / AMD Ryzen 5 (4 cores)
RAM  : 8 GB
Disk : 50 GB SSD
OS   : Windows 10+, Ubuntu 20.04+, macOS 12+
GPU  : ไม่จำเป็น
```

### Recommended (Production — 10 กล้อง)

```
CPU  : AMD Ryzen 5/7 รุ่นใหม่ (6-8 cores) ← เครื่องที่มีอยู่
RAM  : 16 GB ← หลังอัพแล้ว
Disk : 512 GB SSD (snapshots + video clips สะสม)
GPU  : ไม่จำเป็น — OpenVINO CPU เพียงพอ
Network : 100 Mbps LAN (RTSP stream 10 กล้อง ≈ 50-80 Mbps)
```

### RAM Budget (16 GB)

```
OS + background            :  2.0 GB
Python process (main)      :  0.5 GB
OpenVINO + YOLOv11n model  :  0.4 GB  (OpenVINO compress model ได้ดี)
Frame buffers (10 กล้อง)   :  0.5 GB
Object tracker             :  0.2 GB
FastAPI + DB connections   :  0.3 GB
SQLite WAL buffer          :  0.2 GB
Safety margin              :  2.0 GB
──────────────────────────────────────
รวมใช้งาน                 :  6.1 GB
เหลือ headroom             :  9.9 GB  ✅ เพียงพอมาก
```

### Expected Performance (CPU-only, Ryzen + OpenVINO)

```
โมเดล                  FPS (ประมาณ)    หมายเหตุ
─────────────────────────────────────────────────────
YOLOv11n OpenVINO IR   20-35 FPS       เร็วกว่า ONNX ~20-30%
YOLOv11s OpenVINO IR   12-20 FPS       ถ้าต้องการความแม่นยำสูงขึ้น

Strategy: Motion Detection ก่อน → AI เฉพาะกล้องที่มี motion
          → ประหยัด CPU 60-70% ในสถานการณ์ปกติ
```

---

## 6. Architecture Decision Records (ADR)

### ADR-01: Modular Monolith ไม่ใช่ Microservices

```
Status   : Accepted
Context  : ระบบ 10 กล้อง บน 1 เครื่อง ต้องการ latency ต่ำระหว่าง AI → Rules → Alert
Decision : Modular Monolith — แต่ละ module สื่อสารผ่าน MTP Message Bus (in-process)
Consequence:
  ✅ Latency ต่ำมาก (in-process queue ไม่ใช่ network)
  ✅ Deploy ง่าย (1 process)
  ✅ Debug ง่าย (1 log stream)
  ⚠️ Scale horizontal ยากกว่า (แต่ไม่ต้องการตอนนี้)
```

### ADR-02: FastAPI ไม่ใช่ Django

```
Status   : Accepted
Context  : ต้องการ async-first, WebSocket, auto API docs, Pydantic integration
Decision : FastAPI — async native ตั้งแต่ต้น
Rejected : Django REST Framework — sync-first, ต้องเพิ่ม channels สำหรับ WebSocket
```

### ADR-03: ไม่ใช้ Redis สำหรับ Single Host

```
Status   : Accepted
Decision : ใช้ cachetools.TTLCache + DB table แทน
Rationale:
  - Redis = service เพิ่ม → ต้องดูแล, configure, secure, monitor
  - Single host ไม่มี distributed state problem
  - TTLCache ทำงาน in-process เร็วกว่า Redis (ไม่มี network hop)
เพิ่ม Redis เมื่อ: ต้องการ multi-host หรือกล้อง > 50 ตัว
```

### ADR-04: OpenVINO (ไม่ใช่ ONNX Runtime)

```
Status   : Accepted — เปลี่ยนจาก draft แรก
Context  : ตรวจสอบ venv พบ openvino 2026.1.0 ติดตั้งไว้แล้ว
Decision : ใช้ OpenVINO เป็น inference backend หลัก
Rationale:
  - ติดตั้งไว้แล้ว (ไม่ต้องเพิ่ม dependency)
  - OpenVINO 2023+ รองรับ AMD Ryzen (ไม่ใช่ Intel-only อีกต่อไป)
  - เร็วกว่า ONNX Runtime บน CPU ประมาณ 20-30%
  - รองรับ model quantization (INT8) ได้ดีกว่า ลด RAM และเพิ่ม FPS
  - YOLOv11 export เป็น OpenVINO IR ได้โดยตรง (ultralytics รองรับ)
```

### ADR-05: Vue.js + DaisyUI ไม่ใช่ React + Tailwind

```
Status   : Accepted
Context  : เลือก Frontend framework สำหรับ Pilot's Console
Decision : Vue 3 (Composition API) + TypeScript + DaisyUI
Rationale:
  - Vue SFC (Single File Component) อ่านง่ายกว่า — HTML/CSS/JS อยู่ไฟล์เดียว
  - DaisyUI มี component สำเร็จรูป (badge, modal, alert, table) ใช้ได้ทันที
  - DaisyUI มี theme system — ปรับ dark/light mode ง่าย เหมาะกับ console ที่ใช้กลางคืน
  - Pinia (Vue official store) ง่ายกว่า Redux
Rejected : React — JSX verbose กว่า, state management ซับซ้อนกว่า
```

### ADR-06: Playwright สำหรับ E2E Testing

```
Status   : Accepted
Context  : ต้องการ E2E test สำหรับ Pilot's Console
Decision : Playwright — cross-browser, auto-wait, screenshot on failure
Feature ที่ใช้:
  - Codegen: บันทึก user action → generate test code อัตโนมัติ
  - Visual comparison: screenshot diff ตรวจ UI regression
  - AI-assisted: ใช้ locator แบบ semantic (getByRole, getByText) ไม่ใช่ CSS selector
  - Trace viewer: debug test failure ด้วย timeline + network
```

### ADR-07: SQLite WAL → PostgreSQL Migration Path

```
Status   : Accepted
Decision : ใช้ SQLAlchemy ORM ทั้งหมด — ไม่มี raw SQL ที่ SQLite-specific
           Alembic จัดการ migration ทั้งสอง DB
Trigger to migrate: events table > 1M rows หรือ concurrent writes > 10/sec
```

### ADR-08: YOLOv11n เป็น Default Model

```
Status   : Accepted
Decision : YOLOv11n export เป็น OpenVINO IR format
Trade-off: ความแม่นยำต่ำกว่า YOLOv11m แต่ FPS สูงกว่า 3x
           สำหรับ security: detect ช้า 1-2 วิ ยอมรับได้กว่า miss detection
```

---

## 7. Project Structure (Updated)

```
D:\dev\MTSecurity\
│
├── my_env\                    ← Python 3.12.10 virtual environment
│   └── Scripts\
│       ├── python.exe
│       ├── pip.exe
│       └── activate
│
└── my_workspace\              ← Project root
    ├── backend\               ← Python FastAPI (สร้างใน Phase 1)
    │   ├── pyproject.toml
    │   ├── main.py
    │   ├── protocol\
    │   ├── ssot\
    │   ├── ingestion\
    │   ├── ai\
    │   ├── rules\
    │   ├── alerts\
    │   ├── api\
    │   ├── auth\
    │   ├── models\
    │   ├── schemas\
    │   ├── db\
    │   ├── analytics\
    │   ├── migrations\
    │   ├── tests\
    │   └── data\              ← gitignored (db, snapshots, models)
    │
    ├── frontend\              ← Vue 3 + TypeScript + DaisyUI (สร้างใน Phase 5)
    │   ├── package.json
    │   ├── vite.config.ts
    │   ├── src\
    │   │   ├── components\
    │   │   ├── views\
    │   │   ├── stores\        ← Pinia
    │   │   ├── router\        ← Vue Router
    │   │   └── composables\   ← WebSocket, useAlerts, useCameras
    │   └── e2e\               ← Playwright tests
    │       └── tests\
    │           ├── login.spec.ts
    │           ├── alert-queue.spec.ts
    │           └── camera-grid.spec.ts
    │
    └── doc\                   ← Documentation (อยู่แล้ว)
        └── claude_version\
            └── v2\
```

---

## 8. What We Are NOT Using (และทำไม)

```
Technology       เหตุผลที่ไม่ใช้
────────────────────────────────────────────────────────────────
Redis            Single host — ไม่คุ้มค่า overhead (ADR-03)
ONNX Runtime     OpenVINO ติดตั้งแล้ว เร็วกว่า (ADR-04)
React            Vue.js + DaisyUI เหมาะกว่าสำหรับทีมนี้ (ADR-05)
Celery           asyncio queue พอสำหรับ single host
Docker           Development phase ไม่จำเป็น
Kafka/RabbitMQ   Message broker ระดับ enterprise — overkill
GraphQL          REST เพียงพอ
```
