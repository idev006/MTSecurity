# 17 — Test & Audit Plan
### CI Pipeline · Per-Phase Gate · Security Audit · AI Accuracy · Performance · Regression

---

## 1. ภาพรวม Testing Strategy ต่อวงรอบ

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TESTING LIFECYCLE                                  │
│                                                                       │
│  ทุก COMMIT                                                          │
│  └── CI Pipeline: ruff → mypy → pytest unit → coverage check        │
│                                                                       │
│  ทุก FEATURE (merge to main)                                         │
│  └── CI Pipeline + Integration tests + Regression suite              │
│                                                                       │
│  ทุก PHASE (ก่อนปิด Phase)                                          │
│  └── Phase Gate Checklist + Security Audit Point + Performance Check │
│                                                                       │
│  PRE-RELEASE (Phase 6)                                               │
│  └── Full Audit + Load Test + 24h Stability Test + Playwright E2E    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. CI Pipeline (ทุก Commit อัตโนมัติ)

### Backend CI — `backend/.github/workflows/ci.yml` หรือ pre-commit hook

```yaml
# .github/workflows/backend-ci.yml
name: Backend CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          cd backend
          pip install -e ".[dev]"

      - name: Lint (ruff)
        run: ruff check backend/

      - name: Type check (mypy)
        run: mypy backend/ --ignore-missing-imports

      - name: Unit tests + Coverage
        run: |
          cd backend
          pytest tests/unit/ -v \
            --cov=. \
            --cov-fail-under=80 \
            --cov-report=term-missing

      - name: Integration tests
        run: |
          cd backend
          pytest tests/integration/ -v
```

### Pre-commit Hook (Local — ทำก่อน push ทุกครั้ง)

```bash
# backend/.pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: ruff
        name: ruff lint
        entry: ruff check
        language: system
        types: [python]

      - id: ruff-format
        name: ruff format
        entry: ruff format --check
        language: system
        types: [python]

      - id: mypy
        name: mypy type check
        entry: mypy
        language: system
        types: [python]

      - id: pytest-unit
        name: unit tests
        entry: pytest tests/unit/ -q
        language: system
        pass_filenames: false
```

```powershell
# ติดตั้ง (Windows)
pip install pre-commit
pre-commit install
```

### Frontend CI

```yaml
# .github/workflows/frontend-ci.yml
- name: Install
  run: cd frontend && npm ci

- name: Type check
  run: cd frontend && npm run type-check

- name: Lint (ESLint)
  run: cd frontend && npm run lint

- name: Unit tests (Vitest)
  run: cd frontend && npm run test -- --run

- name: Build check
  run: cd frontend && npm run build
```

### CI Pass/Fail Gates

```
Gate                    เกณฑ์ผ่าน               ถ้าไม่ผ่าน
────────────────────────────────────────────────────────────────
ruff lint               0 errors, 0 warnings    ❌ block merge
mypy                    0 errors (strict)        ❌ block merge
pytest unit             100% pass               ❌ block merge
coverage                ≥ 80% overall           ❌ block merge
vitest                  100% pass               ❌ block merge
eslint                  0 errors                ❌ block merge
build                   no error                ❌ block merge
```

---

## 3. Per-Phase Gate Checklist

ก่อนปิด Phase ต้องผ่านทุกข้อ ✅

### Phase 1 Gate: Foundation

```
Code Quality
  ☐ ruff + mypy ผ่าน 0 error
  ☐ coverage ≥ 80% บน protocol/, ssot/, auth/

Unit Tests ต้องผ่านทั้งหมด:
  ☐ test_mtp_message_create()         — สร้าง MTPMessage ได้ครบ fields
  ☐ test_mtp_message_expired()        — is_expired() ทำงานถูก
  ☐ test_bus_subscribe_publish()      — publish → subscriber รับ message
  ☐ test_bus_priority_order()         — CRITICAL ถูก dispatch ก่อน NORMAL
  ☐ test_bus_dead_letter_on_ttl()     — message หมด TTL → dead letter
  ☐ test_config_service_load()        — โหลด config จาก DB ได้
  ☐ test_config_service_update()      — update → cache update → CONFIG_CHANGED publish
  ☐ test_jwt_encode_decode()          — encode → decode → payload ตรงกัน
  ☐ test_jwt_expired()                — token หมดอายุ → JWTError
  ☐ test_password_hash_verify()       — hash → verify ผ่าน
  ☐ test_password_wrong()             — verify wrong password → False

Integration Tests:
  ☐ test_config_change_propagates()  — update zone → CONFIG_CHANGED ถูก received
  ☐ test_db_create_all_tables()      — alembic upgrade head → tables ครบ

Manual Check:
  ☐ python main.py เริ่มต้นได้ ไม่ crash
  ☐ GET /api/health → {"status": "ok"}
```

---

### Phase 2 Gate: Ingestion + AI

```
Unit Tests:
  ☐ test_motion_detector_detects()     — frame มี motion → True
  ☐ test_motion_detector_static()      — frame นิ่ง → False
  ☐ test_frame_processor_resize()      — output size ตรงกับ THUMBNAIL_SIZE
  ☐ test_frame_processor_jpeg()        — output เป็น valid JPEG bytes
  ☐ test_detection_postprocess()       — YOLO raw output → Detection objects
  ☐ test_detection_nms()               — Non-max suppression ลด duplicate bbox

AI Accuracy Gate (ทดสอบกับ test video จริง):
  ☐ Person detection rate ≥ 85%       — จาก 20 frames ที่มีคน
  ☐ False positive rate ≤ 10%         — จาก 20 frames ที่ไม่มีคน
  ☐ Inference time ≤ 100ms/frame      — บน Ryzen CPU
  ☐ FPS ≥ 15 (YOLOv11n)              — single camera, no motion gate

Integration Tests:
  ☐ test_camera_rtsp_connect()        — ต่อกล้อง test (หรือ video file) ได้
  ☐ test_pipeline_frame_to_tracking() — frame → detection → TRACK_UPDATE published
  ☐ test_camera_reconnect()           — simulate disconnect → auto reconnect

Performance Check:
  ☐ 1 camera online: CPU < 30%
  ☐ 1 camera + AI: CPU < 50%
  ☐ RAM usage < 2GB total process

Manual Check:
  ☐ ต่อกล้อง 1 ตัว เห็น bounding box บนภาพ
  ☐ TRACK_UPDATE ปรากฏใน log ทุก detection
```

---

### Phase 3 Gate: Rules + Alerts

```
Unit Tests:
  ☐ test_intrusion_inside()           — centroid อยู่ใน polygon → True
  ☐ test_intrusion_outside()          — centroid นอก polygon → False
  ☐ test_intrusion_boundary()         — centroid บนเส้น → defined behavior
  ☐ test_loitering_threshold()        — dwell_time > threshold → trigger
  ☐ test_loitering_below()            — dwell_time < threshold → no trigger
  ☐ test_line_crossing_direction()    — ข้ามเส้นทิศที่กำหนด → True
  ☐ test_line_crossing_reverse()      — ข้ามทิศตรงข้าม → False (ถ้า configured)
  ☐ test_cooldown_blocks_duplicate()  — alert ซ้ำใน cooldown window → suppressed
  ☐ test_cooldown_expires()           — หลัง cooldown หมด → alert ผ่าน
  ☐ test_schedule_always_on()         — always_on=True → rule active ตลอด
  ☐ test_schedule_active_time()       — เวลาตรง schedule → active
  ☐ test_schedule_inactive_time()     — นอกเวลา → inactive
  ☐ test_schedule_overnight()         — schedule ข้ามวัน 22:00→06:00 ถูกต้อง

Integration Tests:
  ☐ test_intrusion_triggers_alert()   — track เข้าโซน → ALERT_FIRED published
  ☐ test_alert_sends_line()           — ALERT_FIRED → LINE API ถูกเรียก
  ☐ test_alert_sends_discord()        — ALERT_FIRED → Discord webhook ถูกเรียก
  ☐ test_snapshot_has_bbox()          — snapshot มี bounding box วาดถูกต้อง

Alert Accuracy Gate (Manual — ใช้กล้องจริง):
  ☐ เดินเข้าโซน → alert ภายใน 3 วินาที ✅
  ☐ ยืนนิ่งนอกโซน → ไม่มี alert ✅
  ☐ เดินผ่านโซน (< 1 วิ) → ไม่ trigger loitering ✅
  ☐ LINE Notify ได้รับภาพ snapshot ถูกต้อง ✅

Security Audit Point #1:
  ☐ LINE token ไม่ปรากฏใน log
  ☐ Discord webhook URL ไม่ปรากฏใน log
  ☐ Snapshot URL ต้องผ่าน auth (ทดสอบ curl ไม่มี token → 401)
```

---

### Phase 4 Gate: API Core

```
Unit Tests:
  ☐ test_login_success()              — correct credential → 200 + tokens
  ☐ test_login_wrong_password()       — wrong password → 401
  ☐ test_login_rate_limit()           — 6 requests/min → 429
  ☐ test_token_refresh()              — valid refresh → new access token
  ☐ test_token_expired()              — expired token → 401
  ☐ test_token_revoked()              — logout → token blacklisted → 401

Permission Tests (ทดสอบทุก actor ทุก endpoint สำคัญ):
  ☐ test_operator_cannot_edit_zone()  — PATCH /zones/1 → 403
  ☐ test_operator_scoped_cameras()    — GET /events/ → เห็นเฉพาะ cam ที่มอบหมาย
  ☐ test_auditor_readonly()           — POST /events/1/acknowledge → 403
  ☐ test_ext_system_scoped()          — API key scope=events:read → GET /events/ ✅
  ☐ test_ext_system_no_zones()        — API key scope=events:read → GET /zones/ 403

Integration Tests:
  ☐ test_zone_update_propagates()     — PUT /zones/1 → RuleEngine รับ CONFIG_CHANGED
  ☐ test_audit_log_written()          — PUT /zones/1 → audit_log record ถูกสร้าง
  ☐ test_websocket_alert_push()       — ALERT_FIRED → WS client รับ alert message
  ☐ test_actor_permissions_matrix()   — ทดสอบ permission matrix จาก 04_actors_usecases.md

Security Audit Point #2:
  ☐ SQL injection: ส่ง "'; DROP TABLE events;--" → 422 ไม่ใช่ 500
  ☐ Path traversal: GET /events/../../.env → 404 ไม่ใช่ file content
  ☐ XSS: ส่ง <script>alert(1)</script> ใน note → ถูก escape ใน response
  ☐ CORS: origin ที่ไม่ได้ whitelist → 403
  ☐ Audit log: ทุก write operation มี record (ตรวจ 5 endpoints)
  ☐ Rate limit: ทดสอบ login 6 ครั้ง/นาที → 429
```

---

### Phase 5 Gate: Pilot's Console

```
Vitest Unit Tests (Frontend):
  ☐ useAlertSocket: connect → receive alert → store updated
  ☐ useGridStream: receive grid_update → 10 cameras updated
  ☐ useAuth: login → token stored → logout → token cleared
  ☐ CameraCanvas: render bbox ถูกตำแหน่ง (normalized coords)
  ☐ AlertQueue: sort by severity + timestamp

Playwright E2E Tests:
  ☐ e2e/login.spec.ts
      - login ด้วย operator account สำเร็จ
      - login ด้วย password ผิด → error message
      - session expire → redirect to login

  ☐ e2e/camera-grid.spec.ts
      - เห็น thumbnail 10 กล้อง ใน grid
      - คลิก thumbnail → primary feed เปลี่ยน
      - กล้อง offline → thumbnail ขอบสีเทา

  ☐ e2e/alert-flow.spec.ts
      - alert ใหม่ปรากฏใน queue ภายใน 3 วินาที
      - กด ACK → popup note → confirm → alert หายจาก queue
      - กด SILENCE 15m → alert ซ่อน 15 นาที

  ☐ e2e/nlq.spec.ts
      - พิมพ์ query → response ปรากฏภายใน 5 วินาที
      - command query → confirm popup ปรากฏ
      - quick query badge → click → ส่ง query อัตโนมัติ

  ☐ e2e/keyboard.spec.ts
      - Space → ACK alert ล่าสุด
      - กด 1-9 → primary feed เปลี่ยนกล้อง
      - F → fullscreen mode

Performance Check (Browser DevTools):
  ☐ Grid update 3 FPS: CPU usage < 20% (browser)
  ☐ Primary feed 10 FPS: CPU usage < 30% (browser)
  ☐ Memory ไม่โตเกิน 50MB ใน 30 นาที
  ☐ Frame เปลี่ยนทุก 333ms ± 50ms (ไม่กระตุก)

UX Check (Manual):
  ☐ Alert badge กระพริบชัดเจนมองเห็นง่าย
  ☐ Dark theme อ่านได้สบายตา กลางคืน
  ☐ Snapshot popup โหลดภายใน 1 วินาที
  ☐ NLQ response เป็นภาษาไทยเมื่อถามภาษาไทย
```

---

### Phase 6 Gate: Production Hardening

```
Stability Test (24 ชั่วโมง continuous):
  ☐ ระบบไม่ crash ตลอด 24h
  ☐ Memory ไม่ leak (RSS ไม่โตเกิน 200MB ตลอด 24h)
  ☐ CPU average < 70%
  ☐ ไม่มี unhandled exception ใน log

Load Test (10 กล้องพร้อมกัน):
  ☐ 10 RTSP streams connected พร้อมกัน
  ☐ FPS actual ≥ 3 ทุกกล้อง (ใน Console grid)
  ☐ Primary feed FPS ≥ 10
  ☐ Alert latency camera → LINE ≤ 5 วินาที ใน load condition

Failure Recovery Test:
  ☐ ดึงสาย LAN กล้อง 3 → กล้องอื่น 9 ตัวยังทำงาน
  ☐ ต่อสายกลับ → กล้อง 3 reconnect อัตโนมัติ ≤ 30 วินาที
  ☐ Kill AI process → ระบบไม่ crash (DEGRADED mode)
  ☐ Restart ระบบ → resume จาก last known state

Security Audit Point #3 (Final):
  ☐ Security checklist จาก 08_security_guide.md ครบทุกข้อ
  ☐ Penetration test พื้นฐาน:
      - OWASP ZAP scan ผ่าน (0 High severity alerts)
      - Authentication bypass attempt → ไม่ผ่าน
      - Insecure direct object reference → ผ่าน auth check
  ☐ .env ไม่มีใน git history
  ☐ Sensitive data ไม่ปรากฏใน response (password hash, tokens)
  ☐ HTTPS configured (production)

Playwright Full Regression:
  ☐ รัน e2e tests ทั้งหมดจาก Phase 5 → ผ่านทุกข้อ
  ☐ Screenshot comparison: UI ไม่เปลี่ยนจาก baseline
```

---

## 4. Security Audit Points Summary

```
Phase   Audit Point          สิ่งที่ตรวจ
─────────────────────────────────────────────────────────────────
Phase 3  Audit #1            Notification secrets ไม่ leak
                             Snapshot endpoint ต้องการ auth
Phase 4  Audit #2            SQL injection, XSS, Path traversal
                             Permission matrix ทุก actor ทุก endpoint
                             Rate limiting และ CORS
Phase 6  Audit #3 (Final)   Full security checklist (08)
                             OWASP ZAP scan
                             Git history clean
                             HTTPS configured
```

---

## 5. AI Accuracy Acceptance Criteria

### Test Dataset ที่ต้องเตรียม

```
สร้าง: backend/tests/ai_accuracy/
  ├── positive/          # ภาพที่มีคน (≥ 50 frames)
  │   ├── daylight/      # กลางวัน แสงดี
  │   ├── night/         # กลางคืน แสงน้อย
  │   └── partial/       # เห็นแค่บางส่วน (ครึ่งตัว)
  ├── negative/          # ภาพที่ไม่มีคน (≥ 50 frames)
  │   ├── empty_room/
  │   └── moving_objects/ # พัดลม, ใบไม้ไหว
  └── edge_cases/        # กรณียาก
      ├── crowd/          # คนหลายคน
      └── similar_shape/  # หุ่น, รูปภาพคน
```

### Acceptance Criteria

```
Metric                  เกณฑ์ผ่าน     วิธีวัด
──────────────────────────────────────────────────────────────
Person Detection Rate   ≥ 85%         TP / (TP + FN) บน positive set
False Positive Rate     ≤ 10%         FP / (FP + TN) บน negative set
Inference Time (avg)    ≤ 100ms       timeit 100 frames
Inference Time (p95)    ≤ 150ms       percentile 95
FPS (single camera)     ≥ 15          sustained 60 seconds
FPS (10 cameras)        ≥ 5/camera    motion gate active
Tracking Consistency    ≥ 90%         track_id stable across frames
```

### Accuracy Test Script

```python
# tests/ai_accuracy/test_model_accuracy.py
import pytest
from pathlib import Path
from ai.inference_engine import InferenceEngine
from ai.detector import Detector

POSITIVE_DIR = Path("tests/ai_accuracy/positive")
NEGATIVE_DIR = Path("tests/ai_accuracy/negative")
MIN_DETECTION_RATE = 0.85
MAX_FALSE_POSITIVE = 0.10

def test_person_detection_rate():
    engine   = InferenceEngine(model_path="data/models/yolo11n.xml", device="CPU")
    detector = Detector(engine)
    frames   = list(POSITIVE_DIR.glob("**/*.jpg"))

    detected = sum(
        1 for f in frames
        if any(d.class_name == "person" for d in detector.detect(load_frame(f)))
    )
    rate = detected / len(frames)
    assert rate >= MIN_DETECTION_RATE, f"Detection rate {rate:.1%} < {MIN_DETECTION_RATE:.0%}"

def test_false_positive_rate():
    engine   = InferenceEngine(model_path="data/models/yolo11n.xml", device="CPU")
    detector = Detector(engine)
    frames   = list(NEGATIVE_DIR.glob("**/*.jpg"))

    false_pos = sum(
        1 for f in frames
        if any(d.class_name == "person" for d in detector.detect(load_frame(f)))
    )
    rate = false_pos / len(frames)
    assert rate <= MAX_FALSE_POSITIVE, f"False positive rate {rate:.1%} > {MAX_FALSE_POSITIVE:.0%}"

def test_inference_time_p95():
    import numpy as np
    import time
    engine  = InferenceEngine(model_path="data/models/yolo11n.xml", device="CPU")
    frame   = np.zeros((480, 640, 3), dtype=np.uint8)
    times   = []
    for _ in range(100):
        t0 = time.perf_counter()
        engine.infer(frame)
        times.append(time.perf_counter() - t0)
    p95 = np.percentile(times, 95) * 1000   # ms
    assert p95 <= 150, f"P95 inference time {p95:.0f}ms > 150ms"
```

---

## 6. Performance Benchmark Gates

### Backend

```python
# tests/performance/test_streaming.py
import pytest
import asyncio
import time

async def test_frame_processor_throughput():
    """ต้องประมวลผล ≥ 30 frames/sec (headroom เพียงพอสำหรับ 10 cameras × 3fps)"""
    processor = FrameProcessor(stream_cache)
    frame     = generate_test_frame(640, 480)
    count     = 0
    start     = time.perf_counter()

    while time.perf_counter() - start < 1.0:
        await processor.process(camera_id=1, frame=frame, overlay={})
        count += 1

    assert count >= 30, f"Throughput {count} fps < 30 fps"

async def test_websocket_grid_latency():
    """grid update ต้องถึง client ภายใน 500ms หลังจาก frame capture"""
    # simulate: capture → process → broadcast → client receive
    latencies = []
    for _ in range(10):
        t0 = time.perf_counter()
        await simulate_frame_pipeline()
        latencies.append(time.perf_counter() - t0)

    avg_ms = sum(latencies) / len(latencies) * 1000
    assert avg_ms <= 500, f"Avg grid latency {avg_ms:.0f}ms > 500ms"
```

### Frontend (Playwright Performance)

```typescript
// e2e/performance.spec.ts
test('grid render performance', async ({ page }) => {
  await loginAsOperator(page)

  // วัด CPU usage ผ่าน Performance API
  const metrics = await page.evaluate(() => {
    return new Promise(resolve => {
      let frames = 0
      const start = performance.now()
      const count = () => {
        frames++
        if (performance.now() - start < 5000)
          requestAnimationFrame(count)
        else
          resolve({ fps: frames / 5, duration: performance.now() - start })
      }
      requestAnimationFrame(count)
    })
  })
  expect(metrics.fps).toBeGreaterThan(25)   // ≥ 25 render fps
})

test('alert delivery latency', async ({ page }) => {
  await loginAsOperator(page)
  const t0 = Date.now()

  // Simulate alert via API
  await triggerTestAlert()

  // รอ alert ปรากฏใน queue
  await page.waitForSelector('[data-testid="alert-item"]', { timeout: 3000 })
  const latency = Date.now() - t0

  expect(latency).toBeLessThan(3000)   // ≤ 3 วินาที
})
```

---

## 7. Regression Test Suite

รันก่อน merge ทุกครั้ง — ป้องกัน "of เดิมพัง"

```
backend/tests/regression/
  ├── test_mtp_bus_regression.py       # Bus ยัง dispatch ถูก priority
  ├── test_api_auth_regression.py      # Auth flow ยังทำงาน
  ├── test_permission_regression.py    # Permission matrix ไม่เปลี่ยน
  ├── test_alert_flow_regression.py    # Camera → alert ยังทำงาน end-to-end
  └── test_config_propagation.py       # CONFIG_CHANGED ยัง propagate

frontend/e2e/regression/
  ├── login.spec.ts                    # Login ยังทำงาน
  ├── alert-ack.spec.ts                # ACK flow ยังทำงาน
  └── camera-grid.spec.ts              # Grid ยังแสดง 10 กล้อง
```

```powershell
# รัน regression ทั้งหมด (backend + frontend)
# Backend
D:\dev\MTSecurity\my_env\Scripts\Activate.ps1
cd D:\dev\MTSecurity\my_workspace\backend
pytest tests/regression/ -v --tb=short

# Frontend
cd D:\dev\MTSecurity\my_workspace\frontend
npx playwright test e2e/regression/ --reporter=list
```

---

## 8. Test Coverage Requirements

```
Module              Min Coverage    ความสำคัญ
─────────────────────────────────────────────────────
protocol/           90%+           Core — ถ้าพัง ทุกอย่างพัง
rules/behaviors/    90%+           Business logic หลัก
auth/               85%+           Security critical
ssot/               85%+           Data integrity
alerts/             80%+           User-facing critical
api/routers/        75%+           Integration tested ด้วย
ingestion/          60%+           Hardware dependent
ai/                 60%+           Model dependent
nlq/                70%+           LLM dependent
```

---

## 9. Bug Severity & Response Time

```
Severity   ตัวอย่าง                                  ต้องแก้ภายใน
────────────────────────────────────────────────────────────────────
CRITICAL   ระบบ crash, security breach, data loss    ทันที (ชั่วโมงเดียวกัน)
HIGH       Alert ไม่ส่ง, กล้องทั้งหมดไม่ทำงาน      ภายใน 24 ชั่วโมง
MEDIUM     Feature ทำงานไม่ถูก, UI bug              ภายใน Phase ปัจจุบัน
LOW        UX ไม่สวย, text ผิด, minor เท่านั้น      Backlog — Phase ถัดไป
```

---

## 10. Test Execution Summary (ต่อ Phase)

```
Phase     Unit   Integration  AI Accuracy  E2E  Security  Performance  Stability
────────────────────────────────────────────────────────────────────────────────
Phase 1    ✓        ✓            -           -      -           -           -
Phase 2    ✓        ✓            ✓           -      -           ✓           -
Phase 3    ✓        ✓            ✓           -      ✓(#1)       -           -
Phase 4    ✓        ✓            -           -      ✓(#2)       -           -
Phase 5    ✓        ✓            -           ✓      -           ✓           -
Phase 6    ✓        ✓            ✓           ✓      ✓(#3)       ✓           ✓

✓ = ต้องทำก่อนปิด Phase
```
