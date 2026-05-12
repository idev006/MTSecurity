# 11 — Development Guide
### Methodology · Phases · Definition of Done · Coding Standards · Git Workflow

---

## 1. Development Methodology

### Kanban + XP (Extreme Programming บางส่วน)

```
ทำไมถึงเลือก Kanban + XP:

Methodology     เหมาะกับ                       ใช้ไหม
──────────────────────────────────────────────────────────
Waterfall       ทีมใหญ่, requirement fixed      ❌ ไม่เหมาะ
Full Scrum      ทีม 5-9 คน, Sprint ceremony    ❌ overhead สูง
Kanban          ทีมเล็ก, flow-based             ✅ ใช้
XP (บางส่วน)   TDD, CI, small releases         ✅ ใช้บางส่วน
RAD             Prototype-first                 ❌ docs ครบแล้ว
```

### XP Practices ที่นำมาใช้

```
Practice              ใช้ไหม   เหตุผล
──────────────────────────────────────────────────────────
TDD                   ✅       เฉพาะ Rules Engine + Alert logic
                               business logic ซับซ้อน ต้องแน่น
Continuous Integration ✅      pytest + ruff + mypy ทุก commit
Small Releases        ✅       จบแต่ละ Phase = 1 release milestone
Simple Design         ✅       ไม่เพิ่ม abstraction ที่ยังไม่ต้องการ
Refactoring           ✅       ทำได้ตลอดเมื่อมี test ครอบคลุม
Pair Programming      ⚡ optional  ถ้าทีมมี 2 คนขึ้นไป
```

### Kanban Board Columns

```
BACKLOG → READY → IN PROGRESS → REVIEW → DONE
   │         │           │           │       │
   │     (เริ่มได้     (WIP limit    (code    (ผ่าน
   │      ทุก dep      = 1 per      review   Definition
   │      พร้อม)       person)      + test)   of Done)
   │
   └─ รายการจาก Phase Plan ด้านล่าง
```

### WIP Limit

```
In Progress : 1 feature ต่อ 1 คน (ห้ามทำหลายอย่างพร้อมกัน)
Review      : ไม่เกิน 3 items (ถ้าเต็ม — ให้ review ก่อน เพิ่มของใหม่)
```

### Phase Retrospective (ทุกจบ Phase)

```
ถามตัวเอง 3 คำถาม (15 นาที):
  1. อะไรทำได้ดี — ทำต่อไป
  2. อะไรทำได้ไม่ดี — เปลี่ยนใน Phase ถัดไป
  3. อะไรที่ยังไม่ได้ทำ — เพิ่มใน backlog

บันทึกลงใน: doc/retrospectives/phase-N.md
```

---

## 2. Development Phases

Phase ออกแบบตามลำดับ Boot Sequence ใน `07_module_structure.md`
แต่ละ Phase เป็น vertical slice ที่ทดสอบได้

### Phase 1: Foundation (สัปดาห์ที่ 1-2)

```
เป้าหมาย: ระบบสื่อสารภายในทำงานได้ + DB schema พร้อม

Tasks:
  [ ] protocol/mtp.py          — MTPMessage, MTPMsgType, MTPPriority
  [ ] protocol/message_bus.py  — MessageBus (Priority Queue + dispatch)
  [ ] protocol/payloads.py     — Typed payload schemas
  [ ] db/session.py            — SQLAlchemy async engine
  [ ] models/                  — Camera, Zone, Rule, Event, User, AuditLog
  [ ] alembic init + migration 001_initial
  [ ] ssot/config_service.py   — ConfigService (DB-backed cache)
  [ ] ssot/state_registry.py   — RuntimeState (in-memory)
  [ ] auth/jwt_handler.py      — JWT encode/decode
  [ ] auth/password.py         — bcrypt hash/verify

ทดสอบ Phase 1 ผ่านเมื่อ:
  ✓ test_mtp_bus.py ผ่านทุก test
  ✓ DB สร้าง schema ครบทุก table
  ✓ ConfigService โหลด config จาก DB ได้
  ✓ JWT encode → decode → verify ได้
```

### Phase 2: Ingestion + AI (สัปดาห์ที่ 3-5)

```
เป้าหมาย: กล้อง 1 ตัวส่ง detection result ได้ end-to-end

Tasks:
  [ ] ingestion/camera_thread.py   — RTSP capture, 5-10 FPS
  [ ] ingestion/motion_detector.py — MOG2 background subtraction
  [ ] ingestion/frame_buffer.py    — deque(maxlen=1) per camera
  [ ] ingestion/camera_manager.py  — lifecycle management
  [ ] ai/inference_engine.py       — ONNX Runtime wrapper
  [ ] ai/detector.py               — YOLOv11n postprocess
  [ ] ai/tracker.py                — ByteTrack integration
  [ ] ai/pipeline.py               — orchestrate: buffer → detect → track → publish

ทดสอบ Phase 2 ผ่านเมื่อ:
  ✓ ต่อกล้อง 1 ตัวผ่าน RTSP ได้
  ✓ ตรวจจับ person ใน frame ได้ (confidence > 0.5)
  ✓ TRACK_UPDATE message ถูก publish ใน Message Bus
  ✓ FPS ≥ 5 บน CPU Ryzen
```

### Phase 3: Rules + Alerts (สัปดาห์ที่ 6-7)

```
เป้าหมาย: ระบบส่ง LINE alert เมื่อมีคนเข้าโซน

Tasks:
  [ ] rules/behaviors/intrusion.py      — polygon point-in-polygon
  [ ] rules/behaviors/loitering.py      — dwell time accumulator
  [ ] rules/behaviors/line_crossing.py  — tripwire crossing detection
  [ ] rules/rule_engine.py              — subscribe TRACK_UPDATE → evaluate
  [ ] rules/zone_manager.py             — load zones จาก ConfigService
  [ ] rules/schedule_manager.py         — time-based rule activation
  [ ] alerts/alert_manager.py           — debounce + cooldown (TTLCache)
  [ ] alerts/snapshot.py                — annotate frame → JPEG
  [ ] alerts/notifications/line_messaging.py
  [ ] alerts/notifications/webhook_sender.py

ทดสอบ Phase 3 ผ่านเมื่อ:
  ✓ คนเดินเข้าโซน → LINE Notify ส่งได้ภายใน 3 วินาที
  ✓ Cooldown ทำงาน — ไม่ส่งซ้ำภายใน 30 วิ
  ✓ Snapshot มี bounding box ถูกต้อง
  ✓ test_alert_flow.py ผ่าน
```

### Phase 4: API Core (สัปดาห์ที่ 8-9)

```
เป้าหมาย: REST API ครบ + WebSocket ทำงานได้

Tasks:
  [ ] api/app.py                   — FastAPI factory + middleware
  [ ] api/middleware/auth.py       — JWT validation
  [ ] api/middleware/audit.py      — auto audit log
  [ ] api/middleware/rate_limit.py
  [ ] api/routers/auth.py          — login, refresh, logout
  [ ] api/routers/cameras.py
  [ ] api/routers/zones.py
  [ ] api/routers/rules.py
  [ ] api/routers/events.py        — filter, ack, silence, escalate
  [ ] api/routers/analytics.py
  [ ] api/routers/health.py
  [ ] api/websocket/hub.py         — ConnectionManager
  [ ] api/websocket/alert_handler.py

ทดสอบ Phase 4 ผ่านเมื่อ:
  ✓ test_api_events.py ผ่าน
  ✓ test_actor_permissions.py ผ่าน (OPERATOR ไม่สามารถแก้ zone ได้)
  ✓ WebSocket รับ alert event ได้ real-time
  ✓ Audit log บันทึกทุก write operation
```

### Phase 5: Pilot's Console — Frontend (สัปดาห์ที่ 10-12)

```
เป้าหมาย: Operator ใช้งาน Console ได้จริง
Stack   : Vue 3 + TypeScript + DaisyUI + Pinia + Vue Router

Tasks:
  [ ] Vue project setup (Vite + TypeScript + DaisyUI + Tailwind)
  [ ] Login page + JWT storage (Pinia auth store)
  [ ] Vue Router setup (/ = console, /login, /history)
  [ ] WebSocket composable (useAlertSocket, useCameraSocket)
  [ ] Camera grid component (DaisyUI card + badge)
  [ ] Primary feed component + overlay (canvas bounding box, zone)
  [ ] Alert Queue component (DaisyUI alert + badge severity)
  [ ] ACK / Silence / Escalate modal (DaisyUI modal)
  [ ] System Health panel (DaisyUI stats)
  [ ] Dark theme (DaisyUI theme="night" — เหมาะ console กลางคืน)
  [ ] Keyboard shortcuts (Vue onKeydown)
  [ ] Playwright E2E tests (login, alert ack, camera switch)

ทดสอบ Phase 5 ผ่านเมื่อ:
  ✓ Playwright: operator login ได้
  ✓ Playwright: alert pop ขึ้นใน Console ภายใน 2 วิ หลัง detection
  ✓ Playwright: กด ACK แล้ว alert หายออกจาก queue
  ✓ Playwright: กล้อง offline → thumbnail border เปลี่ยนเป็นสีเทา
  ✓ Vitest: useAlertSocket composable unit test ผ่าน
```

### Phase 6: Integration + Hardening (สัปดาห์ที่ 13-14)

```
เป้าหมาย: ระบบเสถียรพร้อม deploy จริง

Tasks:
  [ ] ต่อกล้องครบ 10 ตัว — ทดสอบ load จริง
  [ ] Security checklist จาก 08_security_guide.md
  [ ] Performance profiling — ระบุ bottleneck
  [ ] Error handling ครบ (camera disconnect, AI crash, DB fail)
  [ ] Logging ครบ (structured JSON log)
  [ ] Graceful shutdown
  [ ] .env.example ครบถ้วน

ทดสอบ Phase 6 ผ่านเมื่อ:
  ✓ ระบบทำงาน 24 ชั่วโมงโดยไม่ crash
  ✓ กล้องดับ 1 ตัว — กล้องอื่นทำงานปกติ
  ✓ Memory ไม่ leak หลังรัน 24 ชั่วโมง
  ✓ Security checklist ผ่านทุกข้อ
```

---

## 3. Definition of Done (DoD)

Task ถือว่า Done เมื่อผ่านทุกข้อนี้:

```
Code
  ☐ เขียน type hints ครบทุก function signature
  ☐ ไม่มี mypy error (strict mode)
  ☐ ผ่าน ruff linter (ไม่มี warning)

Test
  ☐ มี unit test ครอบคลุม logic หลัก
  ☐ pytest ผ่านทุก test (ไม่มี skip ที่ไม่มีเหตุผล)
  ☐ Coverage ≥ 80% สำหรับ module ใหม่

Integration
  ☐ ทำงานร่วมกับ component อื่นที่เชื่อมต่อได้จริง
  ☐ ไม่มี circular import

Documentation
  ☐ function ที่มี business logic ซับซ้อน มี docstring สั้นๆ
  ☐ README หรือ doc อัปเดตถ้ามีการเปลี่ยน interface
```

---

## 4. Git Workflow

### Branch Strategy (Trunk-based สำหรับทีมเล็ก)

```
main          ← production-ready เสมอ
  └── feat/phase-1-foundation
  └── feat/camera-thread
  └── feat/rule-intrusion
  └── fix/cooldown-race-condition
```

### Commit Message Format

```
<type>(<scope>): <short description>

type  : feat | fix | test | refactor | docs | chore
scope : protocol | ingestion | ai | rules | alerts | api | auth | ssot

ตัวอย่าง:
  feat(rules): add loitering behavior with dwell accumulator
  fix(alerts): prevent duplicate LINE notify on cooldown edge case
  test(api): add actor permission tests for zone endpoints
  docs(v2): update 09_api_reference with silence endpoint
```

### Pull Request (ถ้าทีม > 1 คน)

```
PR ต้องมี:
  - Description: ทำอะไร ทำไม
  - Test evidence: ภาพ / log output
  - Checklist: DoD ข้างบนครบ

Review: อย่างน้อย 1 คน approve ก่อน merge
```

---

## 5. Coding Standards

### ห้ามทำ (Hard Rules)

```python
# ❌ Direct service call ข้าม boundary
from ai.inference_engine import InferenceEngine
rule_result = InferenceEngine().run(frame)  # rules ไม่รู้จัก ai

# ❌ Raw SQL string
await session.execute(f"SELECT * FROM events WHERE id={event_id}")

# ❌ Blocking I/O ใน async function
import time
async def bad():
    time.sleep(1)        # ใช้ asyncio.sleep แทน
    requests.get(url)    # ใช้ httpx แทน

# ❌ Config hardcode
LINE_TOKEN = "actual_token_here"

# ❌ Exception ที่กลืนแล้วไม่ log
try:
    ...
except Exception:
    pass
```

### ควรทำ (Best Practices)

```python
# ✅ สื่อสารผ่าน Message Bus เสมอ
await bus.publish(MTPMessage(msg_type=MTPMsgType.RULE_TRIGGERED, ...))

# ✅ Config มาจาก Settings
token = settings.line_channel_access_token.get_secret_value()

# ✅ Async I/O ถูกต้อง
async def send_alert():
    await asyncio.sleep(0)         # yield control
    async with httpx.AsyncClient() as client:
        await client.post(url, ...)

# ✅ Exception ที่มีความหมาย
try:
    cap = cv2.VideoCapture(rtsp_url)
except Exception as e:
    logger.error("Camera %d failed to connect: %s", camera_id, e)
    await bus.publish(MTPMessage(msg_type=MTPMsgType.CAMERA_DISCONNECTED, ...))
    raise

# ✅ Type hints ครบ
def get_zones_for_camera(self, camera_id: int) -> list[Zone]:
    ...
```

---

## 6. Testing Strategy

### Pyramid

```
         ┌─────┐
         │ E2E │  ← น้อย (manual + smoke test)
        ┌┴─────┴┐
        │ Integ │  ← ปานกลาง (API + Bus + DB)
       ┌┴───────┴┐
       │  Unit   │  ← มาก (logic, behaviors, parsers)
       └─────────┘
```

### Unit Test — ทดสอบ Logic ล้วน

```python
# tests/unit/test_rule_behaviors.py
def test_intrusion_inside_zone():
    coords = [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]
    assert check_intrusion(centroid=(0.5, 0.5), coords=coords) is True

def test_intrusion_outside_zone():
    coords = [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]
    assert check_intrusion(centroid=(0.1, 0.1), coords=coords) is False

def test_intrusion_on_boundary():
    coords = [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]
    # boundary case — ระบุพฤติกรรมที่ต้องการ
    result = check_intrusion(centroid=(0.2, 0.5), coords=coords)
    assert isinstance(result, bool)  # ต้องได้ผลลัพธ์ชัดเจน ไม่ crash
```

### Integration Test — ทดสอบ Flow จริง

```python
# tests/integration/test_alert_flow.py
async def test_intrusion_triggers_alert(bus, db, config_svc):
    received_alerts = []
    bus.subscribe(MTPMsgType.ALERT_FIRED, lambda m: received_alerts.append(m))

    # Simulate track entering zone
    track_msg = MTPMessage(
        msg_type = MTPMsgType.TRACK_UPDATE,
        payload  = {
            "camera_id": 1,
            "tracks": [{
                "track_id":   42,
                "class_name": "person",
                "confidence": 0.87,
                "bbox":       {"x1": 0.3, "y1": 0.2, "x2": 0.6, "y2": 0.9},
                "dwell_time": 0.5,
            }]
        }
    )
    await bus.publish(track_msg)
    await asyncio.sleep(0.1)

    assert len(received_alerts) == 1
    assert received_alerts[0].payload["event_type"] == "intrusion"
```

### Coverage Target

```
protocol/   : 90%+  (core — ต้องแน่นที่สุด)
rules/      : 85%+  (business logic)
alerts/     : 80%+
api/        : 75%+
ingestion/  : 60%+  (ยาก mock camera จริง)
ai/         : 60%+  (ยาก mock model จริง)
```

---

## 7. Local Development Setup

### Backend

```powershell
# ══════════════════════════════════════
# Windows (PowerShell) — Primary Dev
# ══════════════════════════════════════

# Virtual env อยู่ที่ D:\dev\MTSecurity\my_env\ (Python 3.12.10)
# Project อยู่ที่ D:\dev\MTSecurity\my_workspace\

# 1. Activate virtual environment
D:\dev\MTSecurity\my_env\Scripts\Activate.ps1

# 2. ไปที่ backend folder
cd D:\dev\MTSecurity\my_workspace\backend

# 3. Install dependencies (openvino + numpy ติดตั้งแล้ว)
pip install -e ".[dev]"

# 4. Copy และแก้ .env
copy .env.example .env
# แก้ JWT_SECRET_KEY ด้วย:
# python -c "import secrets; print(secrets.token_hex(32))"

# 5. Initialize DB
python -m alembic upgrade head

# 6. Run development server
uvicorn api.app:app --reload --port 8000

# 7. Run backend tests
pytest tests/ -v --cov=. --cov-report=term-missing

# 8. Lint + type check
ruff check .
mypy .
```

```bash
# ══════════════════════════════════════
# Linux / macOS (bash/zsh)
# ══════════════════════════════════════

# 1. Activate virtual environment
source /opt/mtsecurity/venv/bin/activate    # Linux production
source ~/mtsecurity/venv/bin/activate       # macOS dev

# 2. ไปที่ backend folder
cd ~/mtsecurity/backend

# 3-8. คำสั่งเหมือน Windows ทุกอย่าง (Python cross-platform)
pip install -e ".[dev]"
cp .env.example .env
python -m alembic upgrade head
uvicorn api.app:app --reload --port 8000
pytest tests/ -v --cov=. --cov-report=term-missing
ruff check . && mypy .
```

### Frontend

```powershell
# ไปที่ frontend folder
cd D:\dev\MTSecurity\my_workspace\frontend

# 1. Install Node dependencies
npm install

# 2. Run dev server (Vite HMR)
npm run dev
# → เปิดที่ http://localhost:5173

# 3. Run unit tests (Vitest)
npm run test

# 4. Install Playwright browsers (ครั้งแรก)
npx playwright install

# 5. Run E2E tests (Playwright)
npm run e2e

# 6. Playwright UI mode (debug E2E visually)
npx playwright test --ui

# 7. Build production
npm run build
```

### Playwright — AI-Assisted Testing Tips

```typescript
// e2e/tests/alert-queue.spec.ts
import { test, expect } from '@playwright/test';

test('operator receives alert and acknowledges', async ({ page }) => {
  // ใช้ semantic locator — ไม่ใช้ CSS selector
  await page.goto('http://localhost:5173');
  await page.getByLabel('Username').fill('operator_test');
  await page.getByLabel('Password').fill('P@ssword1234');
  await page.getByRole('button', { name: 'Login' }).click();

  // รอ alert จาก WebSocket (auto-wait built-in)
  await expect(page.getByTestId('alert-queue')).toBeVisible();

  // กด ACK ที่ alert แรก
  await page.getByRole('button', { name: 'ACK' }).first().click();
  await page.getByLabel('Note').fill('ตรวจสอบแล้ว ไม่มีอันตราย');
  await page.getByRole('button', { name: 'Confirm' }).click();

  // ตรวจว่า alert หายออกจาก queue
  await expect(page.getByTestId('alert-queue')).toHaveCount(0);
});

// สร้าง test อัตโนมัติด้วย Playwright Codegen:
// npx playwright codegen http://localhost:5173
```

---

## 8. Milestone Summary

```
Milestone          Phase      เป้าหมาย
────────────────────────────────────────────────────────
M1: Bus is alive   Phase 1    Message Bus ส่ง/รับ message ได้
M2: AI sees        Phase 2    กล้อง 1 ตัว detect คนได้ real-time
M3: Alert works    Phase 3    LINE Notify ส่งได้เมื่อคนเข้าโซน
M4: API ready      Phase 4    REST + WebSocket ครบ ผ่าน permission test
M5: Console live   Phase 5    Operator ใช้งาน Console ได้จริง
M6: Production     Phase 6    10 กล้อง เสถียร 24 ชั่วโมง
```
