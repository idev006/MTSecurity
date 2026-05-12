# MASTER BLUEPRINT BIBLE
## คัมภีร์การสร้างโครงการซอฟต์แวร์
### Universal Framework สำหรับทุกโครงการ ทุกขนาด ทุก Technology

> เขียนโดย: Claude (Anthropic) — จากประสบการณ์ออกแบบ MTSecurity AI-VMS
> ใช้ได้กับ: Web App, API Service, Embedded System, AI Pipeline, Mobile App
> ปรัชญา: "ถ้าตอบ WHY ไม่ได้ — อย่าเพิ่งทำ WHAT"

---

# PART 0 — ปรัชญาพื้นฐาน

## 0.1 กฎสามข้อที่ทุกโครงการต้องมี

```
กฎ 1: ตัดสินใจด้วยเหตุผล ไม่ใช่นิสัย
       ทุก technology choice, architecture decision, naming convention
       ต้องตอบได้ว่า "เลือกเพราะอะไร" และ "ไม่เลือกตัวอื่นเพราะอะไร"

กฎ 2: ออกแบบเพื่อการเปลี่ยนแปลง ไม่ใช่เพื่อความสมบูรณ์แบบ
       ไม่มีการออกแบบที่สมบูรณ์แบบตั้งแต่แรก
       ออกแบบให้เปลี่ยนได้ง่าย ดีกว่าออกแบบให้ถูกต้องตั้งแต่ต้น

กฎ 3: เอกสารคือ code — ต้องอัปเดตพร้อมกัน
       code ที่ไม่มี document = tech debt
       document ที่ไม่ตรงกับ code = อันตรายมากกว่า ไม่มี document
```

## 0.2 Checklist ก่อนเริ่มโครงการใดๆ

```
□ ปัญหาที่แก้คืออะไร? (1 ประโยค ไม่เกินนี้)
□ ใครเป็น primary user? (ระบุตัวตน ไม่ใช่แค่ "ผู้ใช้")
□ Success หน้าตาเป็นอย่างไร? (วัดได้ ไม่ใช่ "ดีขึ้น")
□ มี deadline ไหม? ถ้ามี — ออกแบบ MVP ก่อน full solution
□ อะไรที่ "ไม่ทำ" ในโครงการนี้? (Non-Goals)
□ Hardware/Infrastructure constraint คืออะไร?
```

---

# PART 1 — FOUNDATION PHASE
## "รู้ว่าสร้างอะไร ก่อนสร้าง"

### 1.1 Problem Statement Canvas

```
┌─────────────────────────────────────────────────────┐
│  FOR     [primary user / actor]                      │
│  WHO     [has this problem / need]                   │
│  THE     [product/system name]                       │
│  IS A    [category]                                  │
│  THAT    [key benefit / value proposition]           │
│  UNLIKE  [current alternative]                       │
│  OUR     [key differentiator]                        │
└─────────────────────────────────────────────────────┘

ตัวอย่าง MTSecurity:
  FOR     Security operators and facility admins
  WHO     need real-time awareness of physical security events
  THE     MTSecurity AI-VMS
  IS A    AI-powered video surveillance management system
  THAT    detects and alerts on security events automatically, 24/7
  UNLIKE  traditional CCTV that only records
  OUR     proactive behavior analysis with sub-3-second alerting
```

### 1.2 Goals & Non-Goals Framework

```
Goals (G):   สิ่งที่ระบบต้องทำ — วัดได้
Non-Goals (NG): สิ่งที่ระบบ "จงใจ" ไม่ทำ — ป้องกัน scope creep
Future (F):  สิ่งที่จะทำใน version ถัดไป (commit ให้ชัด)

Format:
  G1  [verb] [object] [measurable outcome]
  NG1 ไม่ทำ [feature] เพราะ [เหตุผล]
  F1  [feature] — planned for Phase 2 / [timeline]
```

### 1.3 Hard Constraints Template

```
HC-HARDWARE:
  CPU, RAM, Storage, Network (ระบุค่าจริง)
  → ผลกระทบต่อ design: [อธิบาย]

HC-LATENCY:
  P50, P95, P99 latency target
  → ผลกระทบต่อ design: [อธิบาย]

HC-COMPLIANCE:
  GDPR, PDPA, ISO, กฎหมายที่เกี่ยวข้อง
  → ผลกระทบต่อ design: [อธิบาย]

HC-DEPENDENCY:
  external system, API, legacy system ที่ต้องใช้ร่วม
  → ผลกระทบต่อ design: [อธิบาย]
```

### 1.4 Quality Attribute Matrix

```
สำหรับทุกโครงการ ต้องตัดสินใจ trade-off ต่อไปนี้:

Attribute       Target          ← ระบุค่าจริง ไม่ใช่ "สูง/ต่ำ"
────────────────────────────────────────────────────────────
Availability    99.X%
Latency (P95)   X ms
Throughput      X req/sec
Data Retention  X days
Consistency     Strong / Eventual
Scalability     Vertical / Horizontal

ถ้า trade-off กัน → ระบุ priority: AVAILABILITY > LATENCY > CONSISTENCY
```

---

# PART 2 — ACTOR PHASE
## "รู้ว่าใครใช้ ก่อนออกแบบ interface"

### 2.1 Actor Identification Framework

```
Human Actors:
  ระดับ 1 (Global/Owner): สิทธิ์สูงสุด, จำนวนน้อย
  ระดับ 2 (Admin): จัดการระบบ, ไม่ manage users
  ระดับ 3 (Operator): ใช้งานหลัก, ไม่ configure
  ระดับ 4 (Viewer/Auditor): อ่านอย่างเดียว

Automated Actors:
  SYSTEM: งานอัตโนมัติ, ไม่ใช่มนุษย์
  CRON: งาน scheduled
  EXTERNAL: ระบบภายนอก (API Client)

สำหรับแต่ละ Actor ต้องกำหนด:
  - ตัวตน: ใครคือคนนี้จริงๆ ในโลกความเป็นจริง
  - ความถี่การใช้งาน: ทุกวัน / รายสัปดาห์ / เฉพาะกิจ
  - Primary concern: เขาต้องการอะไรมากที่สุด
  - สิทธิ์: อะไรทำได้ อะไรทำไม่ได้
  - Scope: เห็นข้อมูลทั้งหมด หรือเฉพาะส่วนที่เกี่ยวข้อง
```

### 2.2 Use Case Template

```
UC-[ACTOR_CODE]-[NUMBER]: [Use Case Name]

Actor:     [actor type]
Trigger:   [what causes this use case]
Pre-cond:  [what must be true before]
Main Flow:
  1. [step 1]
  2. [step 2]
  ...
Alt Flow:  [what happens when main flow fails]
Post-cond: [what is true after success]
Priority:  P0 (MVP) | P1 | P2
```

### 2.3 Permission Matrix Template

```
           ACTOR_1  ACTOR_2  ACTOR_3  ...
─────────────────────────────────────────
resource_1:create   ✓        ✗        ✗
resource_1:read     ✓        ✓        ✓*
resource_1:update   ✓        ✓        ✗
resource_1:delete   ✓        ✗        ✗
action_1            ✓        ✓        ✓
action_2            ✓        ✗        ✗

✓  = full access
✓* = scoped access (กำหนดเงื่อนไข)
✗  = no access
```

---

# PART 3 — ARCHITECTURE PHASE
## "ออกแบบ structure ก่อนเขียน code"

### 3.1 Layered Architecture (OSI-Inspired)

```
ทุกระบบมี layer หลักๆ ดังนี้ (ปรับจำนวนตามความซับซ้อน):

L7 Application   → Business Rules, Use Case Execution
L6 Presentation  → API Contracts, Data Serialization
L5 Session       → State Management, Session Lifecycle
L4 Transport     → Message Delivery, Queue, Retry
L3 Network       → Service Discovery, Routing
L2 Data Link     → Protocol Framing, Encoding
L1 Physical      → Hardware, External Systems, I/O

กฎ: Layer X รู้จักแค่ Layer X-1 และ X+1
    ไม่มี shortcut ข้าม layer
    ทุก cross-layer communication ผ่าน defined interface
```

### 3.2 API-as-Core Principle

```
ถ้าระบบมีหลาย component:
  → ให้ทุก component communicate ผ่าน API/Message Bus
  → ไม่มี direct call ข้าม service boundary
  → ผลลัพธ์: Observability, Testability, Replaceability

ถ้าระบบเล็กและ component เดียว:
  → ใช้ layered function calls ปกติ (ไม่ต้อง bus)
  → แต่ยังต้องมี defined interface ระหว่าง layer
```

### 3.3 Communication Architecture Checklist

```
สำหรับทุกการสื่อสารในระบบ ต้องตอบ:

□ Protocol คืออะไร? (HTTP/WS/MQTT/Queue/direct call)
□ Format คืออะไร? (JSON/MessagePack/Protobuf/binary)
□ Direction คืออะไร? (sync request-response / async publish-subscribe)
□ Error handling คืออะไร? (retry/dead-letter/fail-fast)
□ Timeout คืออะไร? (กำหนดค่าจริง ไม่ใช่ infinity)
□ Authentication คืออะไร? (API Key/JWT/mTLS/internal token)
```

### 3.4 Custom Protocol Decision

```
ควร custom protocol เมื่อ:
  ✓ Standard protocol ไม่ carry metadata ที่ต้องการ (tracing, priority, TTL)
  ✓ ต้องการ message routing ระหว่าง internal components
  ✓ ต้องการ version ของ message format

ไม่ควร custom:
  ✗ Transport layer (TCP, WebSocket) — ใช้ standard
  ✗ ถ้า existing protocol (MQTT, AMQP) ครอบคลุมพอ
  ✗ ถ้าทีมขนาดเล็กและ complexity ไม่คุ้ม

Custom protocol ควรมี:
  - msg_id (uuid)
  - msg_type (enum)
  - source, target
  - timestamp
  - priority
  - ttl (expiry)
  - correlation_id (tracing)
  - version
  - payload (typed per msg_type)
```

### 3.5 SSOT Design Checklist

```
ระบุ "ความจริง" แต่ละประเภทอยู่ที่ไหน:

Configuration (ไม่เปลี่ยนบ่อย)   → DB + cached in ConfigService
Runtime State (เปลี่ยนเร็ว)       → StateRegistry (in-memory)
Event History (append-only)       → Database (events table)
Computed/Derived                  → คำนวณ on-demand, ไม่เก็บ
Temporary (TTL-based)             → Redis / TTLCache

กฎ: ข้อมูลชิ้นเดียวมีที่เก็บที่เดียว ถ้าต้องการหลายที่ = cache
     cache ต้องมี invalidation strategy เสมอ
```

### 3.6 Failure Mode Analysis

```
สำหรับทุก component หลัก ต้องวิเคราะห์:

Component X fails:
  → ผลต่อ Component A: [ยังทำงาน / degraded / ไม่ทำงาน]
  → ผลต่อ Component B: [...]
  → ผลต่อ User: [...]
  → Detection: [health check / timeout / error log]
  → Recovery: [auto-restart / manual / graceful degradation]

ต้องผ่าน test: "ระบบยังทำงานได้บ้างเมื่อ X พัง"
```

### 3.7 Tier Separation

```
ทุกระบบควรแบ่ง tier ที่ scale ต่างกันได้:

Edge Tier       : ใกล้ hardware / user (camera, browser)
Processing Tier : หนัก CPU/GPU (AI, ETL)
Logic Tier      : Business rules, API
Data Tier       : Database, Cache, File storage
Presentation Tier: UI, Mobile, External integration

แต่ละ tier:
  - Deploy ได้อิสระ (ถ้าจำเป็น)
  - Scale ได้อิสระ
  - ล้มเหลวได้โดยไม่ทำให้ tier อื่นล้มทั้งหมด
```

---

# PART 4 — DOMAIN MODELING PHASE
## "ออกแบบ data ก่อน code"

### 4.1 Ubiquitous Language First

```
ก่อน entity diagram ต้องมี glossary:

คำ              นิยามในระบบนี้ (ไม่ใช่นิยามทั่วไป)
──────────────────────────────────────────────────
[Term 1]      : [definition]
[Term 2]      : [definition]
...

กฎ: ทุก class name, method name, field name
    ต้องมาจาก Ubiquitous Language
    ไม่ใช่ terminology ของ programmer (entity, record, object)
```

### 4.2 Entity Design Principles

```
Entity (มี Identity):
  - มี ID ที่คงอยู่ข้ามเวลา
  - สามารถ track change history ได้
  - ตัวอย่าง: Camera, User, Zone

Value Object (ไม่มี Identity):
  - กำหนดด้วย value ของมัน
  - Immutable
  - ตัวอย่าง: BBox, Coordinate, DateRange

Aggregate Root:
  - Entity ที่ own Entity อื่น
  - External ต้องผ่าน Aggregate Root เสมอ
  - ตัวอย่าง: Camera owns Zones, Zone owns Rules
```

### 4.3 Database Design Rules

```
1. ไม่ใช้ Cascade Delete — soft delete ด้วย is_active = false
2. ทุก write timestamp ใช้ UTC — timezone แปลงที่ presentation layer
3. JSON/JSONB สำหรับ flexible schema fields เท่านั้น ไม่ใช่ทุกอย่าง
4. Foreign key ทุก relationship — enforce ที่ DB level
5. Index: timestamp (query หลักของทุกระบบ), FK columns, search columns
6. ไม่ store computed value — คำนวณ on-query
7. NULL meaning: "ไม่มีข้อมูล" ไม่ใช่ "ค่า default"

Database Migration Rules:
  - ทุก schema change ต้องผ่าน migration file (Alembic/Flyway)
  - ไม่ ALTER TABLE manually บน production
  - Migration ต้อง backward compatible (add column = ok, rename = เปลี่ยน 2 steps)
```

### 4.4 Database Strategy Template

```
Phase 1 (Dev/MVP):  [SQLite / H2 / in-memory]
  → ไม่ต้อง install server, ทดสอบเร็ว
  → ข้อจำกัด: [ระบุ]

Phase 2 (Production): [PostgreSQL / MySQL / CockroachDB]
  → เปลี่ยนด้วย: [connection string / env var]
  → Migration effort: [กี่ชั่วโมง]

ORM Layer: [SQLAlchemy / TypeORM / Hibernate]
  → เหตุผล: abstraction ทำให้เปลี่ยน DB ได้
  → ข้อระวัง: ORM hiding N+1 queries
```

---

# PART 5 — IMPLEMENTATION PHASE
## "เขียน code อย่างมีวินัย"

### 5.1 Module Structure Rules

```
1. Dependency Direction: บน → ล่าง เท่านั้น
   ห้าม circular import ทุกกรณี

2. Layer Boundary: ห้าม import ข้าม layer
   ถ้าจำเป็น → ใช้ interface / event / dependency injection

3. Single Responsibility:
   1 module = 1 ความรับผิดชอบ
   ถ้า module name มี "and" หรือ "or" → แยก module

4. Naming Convention:
   module  = lowercase_snake_case
   class   = PascalCase
   function = lowercase_snake_case
   constant = UPPER_SNAKE_CASE
   private = _prefix

5. File Size Limit:
   > 300 lines → พิจารณาแยก
   > 500 lines → ต้องแยก (ยกเว้นมีเหตุผล)
```

### 5.2 Configuration Management

```
Static Config (ต้อง restart เพื่อเปลี่ยน):
  → .env file + Pydantic BaseSettings
  → ไม่ hardcode ใน code

Runtime Config (เปลี่ยนได้ขณะรัน):
  → Database + in-memory cache + change notification
  → ต้องมี change propagation strategy

Secret Management:
  → ไม่เก็บใน code หรือ git repository
  → .env สำหรับ local dev
  → Secret Manager (HashiCorp Vault / AWS Secrets Manager) สำหรับ production
  → .env.example สำหรับ document what's needed (ไม่ใส่ค่าจริง)
```

### 5.3 Error Handling Strategy

```
Levels:
  EXPECTED: input validation, not found, unauthorized
    → return error response (4xx) ไม่ log เป็น error
  OPERATIONAL: external API timeout, DB connection drop
    → log WARNING + retry + fallback
  PROGRAMMING: null pointer, assertion failure, logic error
    → log ERROR + alert + safe shutdown
  CRITICAL: OOM, disk full, corrupted state
    → log CRITICAL + emergency shutdown + notify

Rules:
  - ไม่ swallow exception โดยไม่ log
  - ไม่ catch Exception ทั่วไปในระดับ business logic
  - Error message ต้อง actionable ("disk full: 0 bytes remaining")
  - ไม่ expose internal error detail ไปยัง external API
```

### 5.4 Logging Strategy

```
Level     | ใช้เมื่อ                              | ปริมาณ
──────────────────────────────────────────────────────────
DEBUG     | ทุก step ของ algorithm (dev เท่านั้น) | สูงมาก
INFO      | events สำคัญ (start, connect, alert)  | ปานกลาง
WARNING   | unusual แต่ recoverable               | น้อย
ERROR     | failure ที่ต้องการ attention           | น้อยมาก
CRITICAL  | system cannot continue               | หายาก

Format: [timestamp] [level] [service] [msg] [key=value ...]
ตัวอย่าง: 2026-05-07T22:14:02Z INFO alert.manager fired event_id=1234 camera_id=3

Rules:
  - ไม่ log sensitive data (password, token, PII)
  - Structured logging (JSON) สำหรับ production
  - Correlation ID ใน log เพื่อ trace request chain
```

### 5.5 Testing Pyramid

```
         /\
        /E2E\          ← น้อย (5%) แต่ critical path
       /──────\
      /Integrat\       ← ปานกลาง (25%) ต้อง real DB/API
     /──────────\
    /  Unit Tests \    ← มาก (70%) เร็ว, isolated
   /────────────────\

Unit Test Rules:
  - 1 test = 1 behavior
  - Arrange / Act / Assert pattern
  - ไม่ test implementation detail — test behavior
  - Mock ที่ boundary เท่านั้น (external API, DB)

Integration Test Rules:
  - ใช้ test DB (SQLite :memory: ถ้า dev phase)
  - ทดสอบ happy path + most common error path
  - Seed data ใน fixture ไม่ใช่ใน test function

Performance Test:
  - ทดสอบบน hardware ที่ใกล้เคียง production
  - วัด P50, P95, P99 ไม่ใช่แค่ average
  - ทดสอบ sustained load ไม่ใช่แค่ peak
```

---

# PART 6 — OPERATIONS PHASE
## "ออกแบบให้ operate ได้ ไม่ใช่แค่ deploy ได้"

### 6.1 Observability Triad

```
Logs    : What happened? (event-based)
Metrics : How is the system? (numeric, time-series)
Traces  : Why did it happen? (request journey)

ทุกระบบต้องมี:
  □ Health check endpoint (GET /health → {status, components})
  □ Key metrics exposed (request rate, error rate, latency)
  □ Structured logs with correlation ID
  □ Alerting rule สำหรับ metric ที่เกิน threshold
```

### 6.2 Health Check Design

```python
# GET /health → 200 OK or 503 Service Unavailable
{
  "status": "ok" | "degraded" | "down",
  "version": "1.2.3",
  "uptime_seconds": 3600,
  "components": {
    "database":  {"status": "ok",       "latency_ms": 2},
    "cache":     {"status": "ok",       "latency_ms": 0.5},
    "ai_engine": {"status": "degraded", "fps": 0.8, "target": 1.0},
    "cameras":   {"status": "ok",       "online": 9, "total": 10}
  }
}

Rules:
  - Health check ต้องไม่ require authentication
  - Timeout: check แต่ละ component ≤ 1 second
  - ถ้า critical component down → HTTP 503
  - ถ้า non-critical degraded → HTTP 200 + status: "degraded"
```

### 6.3 Graceful Shutdown

```
เมื่อได้รับ SIGTERM:
  1. Stop accepting new requests
  2. Finish in-flight requests (timeout: 30s)
  3. Flush queued messages
  4. Close DB connections
  5. Release file handles
  6. Log "shutdown complete"
  7. Exit(0)

ไม่ควร:
  - Kill process ทันทีโดยไม่ flush
  - รอ indefinitely (ต้องมี max shutdown timeout)
```

### 6.4 Data Retention & Cleanup

```
กำหนดสำหรับทุก data type:
  - Retention period (เก็บนานแค่ไหน)
  - Archive policy (เก็บในรูปแบบอื่นหลังจากนั้น)
  - Purge policy (ลบเมื่อไหร่)
  - Audit log (เก็บนานกว่า business data เสมอ)

ต้องมี scheduled cleanup job ที่:
  - รันอัตโนมัติ (cron)
  - Log ว่าลบอะไรไปเท่าไหร่
  - Alert ถ้า disk usage > threshold
```

---

# PART 7 — DOCUMENTATION PHASE
## "เขียน doc เพื่อคนอ่าน ไม่ใช่เพื่อ compliance"

### 7.1 Document Set ขั้นต่ำ

```
ทุกโครงการต้องมี:

README.md           ← 5 นาทีแรก: ทำอะไร, ติดตั้งยังไง, รันยังไง
ARCHITECTURE.md     ← ภาพรวม: layers, components, การตัดสินใจสำคัญ
ACTORS.md           ← ใครใช้ระบบ, ทำอะไรได้
API.md / OpenAPI    ← contract ของ API ทุก endpoint
RUNBOOK.md          ← how to operate: deploy, backup, recover
CHANGELOG.md        ← อะไรเปลี่ยนใน version ไหน
.env.example        ← config ที่ต้องการทั้งหมด (ไม่ใส่ secret)
```

### 7.2 Architecture Decision Record (ADR)

```
ทุกการตัดสินใจสำคัญต้องมี ADR:

ADR-[number]: [ชื่อการตัดสินใจ]
Status: [proposed | accepted | deprecated | superseded]
Date: YYYY-MM-DD

Context:
  ทำไมต้องตัดสินใจ, constraints คืออะไร

Decision:
  เลือกอะไร

Rationale:
  เพราะอะไร, ทำไมไม่เลือกตัวอื่น

Consequences:
  ผลดี, ผลเสีย, สิ่งที่ต้องทำเพิ่ม
```

### 7.3 Documentation Anti-patterns

```
ห้ามทำ:
  ✗ Document ที่อธิบาย WHAT โดยไม่มี WHY
  ✗ Document ที่ copy-paste code แล้ว paraphrase
  ✗ Document ที่ไม่มีวันที่และ version
  ✗ Document ที่ outdated และไม่มีใคร maintain
  ✗ ใช้ "etc.", "and so on", "obviously" ใน technical doc
  ✗ Diagram ที่ไม่มี legend

ควรทำ:
  ✓ Document เฉพาะ "WHY" และ "non-obvious HOW"
  ✓ Link ไปยัง code แทนการ copy
  ✓ บอก "สิ่งที่ระบบนี้ไม่ทำ" ให้ชัดเจน
  ✓ Update doc พร้อมกับ code (same PR)
  ✓ มี example ที่ runnable ใน doc
```

---

# PART 8 — PHASE GATES
## "Checklist ก่อนไปต่อแต่ละ Phase"

### Gate 0 → 1: จาก Idea ไป Foundation

```
□ Problem statement เขียนได้ใน 1 ประโยค
□ Primary user ระบุได้ชัดเจน (ไม่ใช่ "ทุกคน")
□ Success criteria วัดได้ (ไม่ใช่ "ดีขึ้น")
□ Non-goals ระบุไว้แล้ว
□ Hard constraints รู้ทั้งหมด
□ Budget/timeline realistic
```

### Gate 1 → 2: จาก Foundation ไป Architecture

```
□ Goals ทุกข้อมีคนรับผิดชอบ
□ Quality attributes ตัดสินใจแล้ว (latency vs consistency)
□ Compliance requirements รู้ทั้งหมด
□ ทีมเห็นด้วยกับ goals ทุกข้อ
```

### Gate 2 → 3: จาก Architecture ไป Domain Model

```
□ Layer boundary ชัดเจน (ใครรู้จักใคร)
□ Communication protocol ตัดสินใจแล้ว
□ Failure mode ของทุก component วิเคราะห์แล้ว
□ Deployment topology ชัดเจน
□ SSOT กำหนดแล้ว (ความจริงแต่ละอย่างอยู่ที่ไหน)
```

### Gate 3 → 4: จาก Domain Model ไป Implementation

```
□ Ubiquitous language มี glossary ครบ
□ Entity relationships ชัดเจน
□ API contracts เขียน (OpenAPI / Pydantic) ก่อน implement
□ Database schema reviewed โดยทุกคนที่เกี่ยวข้อง
□ Migration strategy ตัดสินใจแล้ว (SQLite → PostgreSQL)
```

### Gate 4 → 5: จาก Implementation ไป Operations

```
□ Unit test coverage > 70% (core business logic)
□ Integration test ครอบคลุม happy path ทุก use case
□ Health check endpoint ทำงาน
□ Logging structured และ queryable
□ Graceful shutdown ทำงาน
□ .env.example ครบทุก config
□ RUNBOOK เขียนแล้ว
```

### Gate 5 → Production

```
□ Load test ผ่านที่ 2× expected traffic
□ Failure scenario test (kill DB, kill AI, disconnect camera)
□ Backup/restore ทดสอบแล้ว
□ Monitoring alert ตั้งไว้แล้ว
□ Rollback procedure ทดสอบแล้ว
□ Security: no hardcoded secrets, input validation ทุก boundary
□ Data retention policy บังคับใช้
```

---

# PART 9 — PRINCIPLES SUMMARY
## "จำ 10 ข้อนี้ ก็เพียงพอ"

```
1.  WHY ก่อน WHAT ก่อน HOW — เสมอ
2.  Design เพื่อการเปลี่ยนแปลง ไม่ใช่ความสมบูรณ์แบบ
3.  Loose coupling ผ่าน defined interface ไม่ใช่ abstraction
4.  SSOT: ความจริงมีที่เดียว, ที่อื่นคือ cache
5.  Actor ก่อน Feature — รู้ว่าใครใช้ ก่อนออกแบบ
6.  Fail gracefully — ออกแบบ failure path ให้ดีเท่า happy path
7.  Observe everything — log, metric, trace คือ safety net
8.  Document WHY ไม่ใช่ WHAT — code อธิบาย WHAT ได้แล้ว
9.  Test behavior ไม่ใช่ implementation — refactor ได้โดยไม่แก้ test
10. Phase gate — อย่าเดินหน้าถ้า checklist ไม่ผ่าน
```

---

*MASTER BLUEPRINT BIBLE v1.0*
*Created: 2026-05-07*
*Based on: MTSecurity AI-VMS Design Experience*
*Next review: เมื่อเจอ pattern ใหม่ที่สำคัญ*
