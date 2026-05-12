# 15 — Natural Language Query (NLQ) Design
### สอบถามระบบด้วยภาษาธรรมชาติ · Claude API · RAG over Events

---

## 1. แนวคิด

```
User พิมพ์: "มีใครเข้าโซนอันตรายหลังเที่ยงคืนบ้าง?"
ระบบตอบ : "พบ 3 เหตุการณ์ ระหว่าง 00:12–02:45 น.
           - CAM-03 ประตูหลัง เวลา 00:12 น. (person, confidence 89%)
           - CAM-01 ประตูหน้า เวลา 01:30 น. (person, confidence 91%)
           - CAM-03 ประตูหลัง เวลา 02:45 น. (person, confidence 78%)
           [ดูภาพ] [ดูในประวัติ]"

User พิมพ์: "กล้องตัวไหนแจ้งเตือนมากที่สุดสัปดาห์นี้?"
ระบบตอบ : "CAM-03 ประตูหลัง มีแจ้งเตือนมากที่สุด 47 ครั้ง
           รองลงมา: CAM-01 (23 ครั้ง), CAM-07 (15 ครั้ง)"

User พิมพ์: "ปิดการแจ้งเตือนกล้อง 3 ไว้ก่อน 30 นาที"
ระบบตอบ : "✅ ปิดการแจ้งเตือน CAM-03 ประตูหลัง ถึง 23:14 น."
           [ยืนยัน] [ยกเลิก]  ← action ที่เปลี่ยนแปลงระบบต้องยืนยัน
```

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     NLQ PIPELINE                                 │
│                                                                   │
│  User Input (Thai/English)                                       │
│       │                                                           │
│       ▼                                                           │
│  ┌─────────────────────┐                                         │
│  │   Intent Classifier  │  ← Claude Haiku (fast, cheap)         │
│  │   Query / Command /  │    classify: query|command|ambiguous   │
│  │   Ambiguous          │                                         │
│  └──────────┬──────────┘                                         │
│             │                                                     │
│      ┌──────┴──────┐                                             │
│      │             │                                             │
│      ▼             ▼                                             │
│  ┌────────┐  ┌──────────────────┐                               │
│  │ QUERY  │  │    COMMAND        │                               │
│  │        │  │ (ต้องยืนยัน)     │                               │
│  └───┬────┘  └──────┬───────────┘                               │
│      │              │                                            │
│      ▼              ▼                                            │
│  ┌──────────────────────────────┐                               │
│  │      SQL Generator           │  ← Claude Haiku               │
│  │  NL → structured query params│    generate filter params     │
│  │  ไม่ generate raw SQL        │    ไม่ใช่ raw SQL (injection) │
│  └──────────────┬───────────────┘                               │
│                 │                                                 │
│                 ▼                                                 │
│  ┌──────────────────────────────┐                               │
│  │      QueryExecutor           │  ← ใช้ SQLAlchemy ORM         │
│  │  execute safe DB query       │    ไม่ใช่ raw SQL             │
│  │  apply actor permission      │    enforce camera_ids scope   │
│  └──────────────┬───────────────┘                               │
│                 │                                                 │
│                 ▼                                                 │
│  ┌──────────────────────────────┐                               │
│  │      Response Formatter      │  ← Claude Haiku               │
│  │  results → Thai/English text │    format + summarize         │
│  │  + action buttons            │                               │
│  └──────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. ทำไมถึงใช้ Claude API

```
ทางเลือก              ข้อดี                    ข้อเสีย
────────────────────────────────────────────────────────────────────
Claude API (Haiku)    เร็ว, ถูก, Thai ดี       ต้องการ internet
                      ไม่ต้องการ GPU           API key + cost
                      Anthropic ecosystem

Local LLM (Ollama)    Offline, ไม่มี API cost  ต้องการ RAM 8GB+
                                               GPU ช่วยมาก
                                               Thai อาจไม่ดี

Rule-based parser     เร็ว, offline            รองรับ query จำกัด
                      ไม่ต้องการ LLM           ต้องเขียน parser

เลือก: Claude API (Haiku) — Thai language ดีมาก, ถูก, เหมาะกับ
       security query ที่ไม่ซับซ้อน
       Cost estimate: ~$0.001 per query × 1000 queries/month ≈ $1/month
```

---

## 4. Claude API Integration

```python
# nlq/claude_client.py
import anthropic
from pydantic import BaseModel

client = anthropic.Anthropic(api_key=settings.anthropic_api_key.get_secret_value())

SYSTEM_PROMPT = """
คุณคือ AI assistant สำหรับระบบกล้องวงจรปิด MTSecurity
หน้าที่: ช่วย operator ค้นหาเหตุการณ์และจัดการระบบด้วยภาษาธรรมชาติ

ข้อมูลระบบ:
- กล้อง: {cameras}
- โซน: {zones}
- เวลาปัจจุบัน: {current_time}
- Actor: {actor_type} (สิทธิ์: {permissions})

กฎสำคัญ:
1. ตอบเป็นภาษาเดียวกับที่ user ถาม (ไทย/อังกฤษ)
2. ถ้าเป็น command ที่เปลี่ยนแปลงระบบ ต้องขอยืนยันก่อน
3. ไม่เปิดเผยข้อมูลกล้องที่ actor ไม่มีสิทธิ์เข้าถึง
4. ถ้าไม่เข้าใจ ให้บอกว่าไม่เข้าใจ อย่าเดา
"""

class NLQIntent(BaseModel):
    intent_type:  str     # "query" | "command" | "ambiguous"
    confidence:   float
    query_params: dict    # สำหรับ query: {camera_id, event_type, date_from, date_to, ...}
    command:      dict    # สำหรับ command: {action, target, params}
    clarification_needed: str | None

async def classify_and_parse(
    user_input: str,
    context: dict          # cameras, zones, actor info
) -> NLQIntent:
    response = client.messages.create(
        model  = "claude-haiku-4-5-20251001",   # เร็วที่สุด ถูกที่สุด
        max_tokens = 500,
        system = SYSTEM_PROMPT.format(**context),
        messages = [{
            "role":    "user",
            "content": f"""
วิเคราะห์คำถามนี้และส่งกลับเป็น JSON:

คำถาม: "{user_input}"

JSON format:
{{
  "intent_type": "query" หรือ "command" หรือ "ambiguous",
  "confidence": 0.0-1.0,
  "query_params": {{
    "camera_ids": [1,2] หรือ null (null=ทุกกล้อง),
    "event_type": "intrusion" หรือ null,
    "date_from": "ISO8601" หรือ null,
    "date_to": "ISO8601" หรือ null,
    "object_class": "person" หรือ null,
    "is_acknowledged": true/false หรือ null,
    "limit": 10
  }},
  "command": {{
    "action": "silence" หรือ "acknowledge" หรือ "escalate" หรือ null,
    "target_camera_id": 3 หรือ null,
    "duration_minutes": 30 หรือ null
  }},
  "clarification_needed": "ต้องการข้อมูลเพิ่มเติมอะไร" หรือ null
}}
"""
        }]
    )
    return NLQIntent.model_validate_json(response.content[0].text)


async def format_response(
    query_params: dict,
    results: list[dict],
    user_input: str,
    context: dict
) -> str:
    """แปลง DB results เป็นภาษาธรรมชาติ"""
    response = client.messages.create(
        model  = "claude-haiku-4-5-20251001",
        max_tokens = 300,
        system = SYSTEM_PROMPT.format(**context),
        messages = [{
            "role": "user",
            "content": f"""
คำถามของ user: "{user_input}"
ผลลัพธ์จาก DB: {results}

กรุณาสรุปผลลัพธ์เป็นภาษาเดียวกับคำถาม กระชับ ได้ใจความ
ถ้าไม่มีผลลัพธ์ให้บอกว่าไม่พบข้อมูล
"""
        }]
    )
    return response.content[0].text
```

---

## 5. Query Executor (Safe SQL via ORM)

```python
# nlq/query_executor.py
from sqlalchemy import select, and_
from models import Event, Camera

class NLQQueryExecutor:
    def __init__(self, db_session, actor: dict):
        self._db     = db_session
        self._actor  = actor
        # enforce camera scope
        self._allowed_cameras = (
            actor["camera_ids"] if actor["camera_ids"] else None  # None = all
        )

    async def execute(self, params: dict) -> list[dict]:
        # Build query ด้วย ORM — ไม่มี SQL injection
        conditions = []

        # Camera scope enforcement (security)
        if self._allowed_cameras:
            conditions.append(Event.camera_id.in_(self._allowed_cameras))

        if params.get("camera_ids"):
            requested = set(params["camera_ids"])
            if self._allowed_cameras:
                allowed   = set(self._allowed_cameras)
                requested = requested & allowed   # intersection — ปลอดภัย
            conditions.append(Event.camera_id.in_(list(requested)))

        if params.get("event_type"):
            conditions.append(Event.event_type == params["event_type"])
        if params.get("object_class"):
            conditions.append(Event.object_class == params["object_class"])
        if params.get("date_from"):
            conditions.append(Event.occurred_at >= params["date_from"])
        if params.get("date_to"):
            conditions.append(Event.occurred_at <= params["date_to"])
        if params.get("is_acknowledged") is not None:
            conditions.append(Event.is_acknowledged == params["is_acknowledged"])

        stmt = (
            select(Event)
            .where(and_(*conditions))
            .order_by(Event.occurred_at.desc())
            .limit(min(params.get("limit", 10), 50))   # max 50 results
        )
        result = await self._db.execute(stmt)
        events = result.scalars().all()
        return [self._format_event(e) for e in events]

    def _format_event(self, event: Event) -> dict:
        return {
            "id":          event.id,
            "camera_name": event.camera.name,
            "event_type":  event.event_type,
            "object_class": event.object_class,
            "confidence":  event.confidence,
            "occurred_at": event.occurred_at.isoformat(),
            "is_acknowledged": event.is_acknowledged,
            "snapshot_url": f"/api/v1/events/{event.id}/snapshot",
        }
```

---

## 6. API Endpoint

### POST /api/v1/nlq/query

```
สิทธิ์  : superadmin, admin, operator (scoped), auditor
Rate    : 20 req/minute per actor
หมายเหตุ: Command ที่เปลี่ยนแปลงระบบต้องผ่าน confirm endpoint แยก
```

**Request**
```json
{
  "query": "มีใครเข้าโซนอันตรายหลังเที่ยงคืนบ้าง?",
  "session_id": "nlq-abc-123"
}
```

**Response 200 — Query result**
```json
{
  "intent_type": "query",
  "answer": "พบ 3 เหตุการณ์ในช่วง 00:12–02:45 น.\n- CAM-03 เวลา 00:12 น. ...",
  "events": [
    {
      "id":           1001,
      "camera_name":  "CAM-03 ประตูหลัง",
      "event_type":   "intrusion",
      "object_class": "person",
      "confidence":   0.89,
      "occurred_at":  "2025-05-11T00:12:00Z",
      "snapshot_url": "/api/v1/events/1001/snapshot"
    }
  ],
  "total_found": 3,
  "session_id":  "nlq-abc-123"
}
```

**Response 200 — Command (requires confirmation)**
```json
{
  "intent_type": "command",
  "answer": "ต้องการปิดการแจ้งเตือน CAM-03 ประตูหลัง เป็นเวลา 30 นาที ใช่หรือไม่?",
  "requires_confirmation": true,
  "pending_command": {
    "action":      "silence",
    "camera_id":   3,
    "duration_min": 30
  },
  "confirm_token": "cmd-xyz-789",
  "session_id":    "nlq-abc-123"
}
```

### POST /api/v1/nlq/confirm

```
สิทธิ์  : ต้องตรงกับ actor ที่สร้าง pending_command
```

**Request**
```json
{
  "confirm_token": "cmd-xyz-789",
  "confirmed":     true
}
```

---

## 7. Frontend NLQ Panel (Vue + DaisyUI)

```vue
<!-- components/NLQPanel.vue -->
<template>
  <div class="card bg-base-200 shadow-xl">
    <div class="card-body p-3">
      <h3 class="card-title text-sm">🤖 สอบถามระบบ</h3>

      <!-- Chat history -->
      <div class="space-y-2 max-h-48 overflow-y-auto" ref="chatContainer">
        <div v-for="msg in messages" :key="msg.id"
             :class="msg.role === 'user' ? 'chat chat-end' : 'chat chat-start'">
          <div :class="msg.role === 'user' ? 'chat-bubble chat-bubble-primary'
                                           : 'chat-bubble'">
            {{ msg.text }}
          </div>

          <!-- Event cards ใน response -->
          <div v-if="msg.events?.length" class="mt-1 space-y-1">
            <div v-for="ev in msg.events" :key="ev.id"
                 class="alert alert-sm alert-info py-1 px-2 cursor-pointer"
                 @click="viewEvent(ev)">
              📷 {{ ev.camera_name }} · {{ ev.event_type }}
              · {{ formatTime(ev.occurred_at) }}
            </div>
          </div>

          <!-- Confirmation buttons -->
          <div v-if="msg.requires_confirmation" class="flex gap-2 mt-1">
            <button class="btn btn-success btn-xs"
                    @click="confirmCommand(msg.confirm_token, true)">
              ✅ ยืนยัน
            </button>
            <button class="btn btn-error btn-xs"
                    @click="confirmCommand(msg.confirm_token, false)">
              ❌ ยกเลิก
            </button>
          </div>
        </div>

        <!-- Loading indicator -->
        <div v-if="isLoading" class="chat chat-start">
          <div class="chat-bubble">
            <span class="loading loading-dots loading-sm"></span>
          </div>
        </div>
      </div>

      <!-- Input -->
      <div class="flex gap-2">
        <input v-model="inputText"
               type="text"
               class="input input-sm input-bordered flex-1"
               placeholder="ถามอะไรก็ได้... เช่น มีคนเข้าโซนอันตรายบ้างไหม?"
               @keydown.enter="sendQuery"
               :disabled="isLoading" />
        <button class="btn btn-primary btn-sm"
                @click="sendQuery"
                :disabled="isLoading || !inputText.trim()">
          ส่ง
        </button>
      </div>

      <!-- Quick queries (DaisyUI badge) -->
      <div class="flex flex-wrap gap-1 mt-1">
        <span v-for="q in quickQueries" :key="q"
              class="badge badge-outline badge-sm cursor-pointer hover:badge-primary"
              @click="inputText = q; sendQuery()">
          {{ q }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const quickQueries = [
  'แจ้งเตือนวันนี้มีกี่ครั้ง?',
  'กล้องตัวไหนแจ้งเตือนมากสุด?',
  'มีเหตุการณ์ที่ยังไม่ได้รับทราบ?',
  'CAM-03 เมื่อคืนมีอะไรบ้าง?',
]
</script>
```

---

## 8. Supported Query Examples

### Query (ค้นหาข้อมูล)

```
ภาษาไทย                                     แปลงเป็น
──────────────────────────────────────────────────────────────────────
"มีใครเข้าโซนอันตรายหลังเที่ยงคืน"    → event_type=intrusion, date_from=00:00
"กล้อง 3 เมื่อกี้มีอะไรบ้าง"          → camera_id=3, date_from=now-1h
"เหตุการณ์ที่ยังไม่ได้รับทราบ"        → is_acknowledged=false
"วันนี้มีรถเข้าออกกี่คัน"             → object_class=car, date_from=today
"สัปดาห์นี้กล้องไหนแจ้งเตือนมากสุด"  → analytics/summary + sort
"ทะเบียน กข-1234 เข้ามาครั้งสุดท้ายเมื่อไหร่" → lpr_events query
```

### Command (เปลี่ยนแปลงระบบ — ต้องยืนยัน)

```
"ปิดกล้อง 3 ไว้ก่อน 1 ชั่วโมง"       → silence camera 3 for 60 min
"รับทราบแจ้งเตือนทั้งหมดของกล้อง 1"  → bulk acknowledge camera 1
"ส่งต่อเหตุการณ์นี้ให้หัวหน้า"        → escalate event
```

### Out of Scope (ตอบว่าทำไม่ได้)

```
"เปิด/ปิดกล้อง" (ต้องเป็น Admin)     → ตอบ: ไม่มีสิทธิ์
"แก้ไขกฎการแจ้งเตือน"               → ตอบ: กรุณาไปที่หน้าตั้งค่า
"ดูรหัสผ่านของระบบ"                  → ตอบ: ไม่สามารถทำได้
```

---

## 9. .env เพิ่มเติม

```bash
# NLQ Configuration
ANTHROPIC_API_KEY=sk-ant-...        # ต้องมี
NLQ_ENABLED=true                    # ปิด/เปิดฟีเจอร์
NLQ_MAX_RESULTS=20                  # จำกัด result ต่อ query
NLQ_COMMAND_TIMEOUT_SEC=30          # confirm timeout
```
