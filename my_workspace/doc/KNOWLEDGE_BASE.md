# MTSecurity — Knowledge Base

> เอกสารอ้างอิงสถาปัตยกรรม, รูปแบบการออกแบบ, ปัญหาที่พบบ่อย และแนวทางแก้ไข  
> ใช้เป็น onboarding guide สำหรับนักพัฒนาใหม่ และ reference สำหรับ debugging

---

## สารบัญ

1. [ภาพรวมสถาปัตยกรรม](#1-ภาพรวมสถาปัตยกรรม)
2. [Detection Pipeline — ตั้งแต่กล้องถึง Alert](#2-detection-pipeline)
3. [MessageBus — กฎการใช้งาน](#3-messagebus)
4. [Cooldown & Track ID System](#4-cooldown--track-id-system)
5. [Video Evidence — Snapshot & Clip](#5-video-evidence--snapshot--clip)
6. [WebSocket Real-time Layer](#6-websocket-real-time-layer)
7. [Live-reload Settings Pattern](#7-live-reload-settings-pattern)
8. [ปัญหาที่พบบ่อย (Pitfalls)](#8-ปัญหาที่พบบ่อย-pitfalls)
9. [Debugging Guide](#9-debugging-guide)
10. [System Settings — ตารางอ้างอิง](#10-system-settings--ตารางอ้างอิง)
11. [การ์ดสรุป Bug Index](#11-การ์ดสรุป-bug-index)

---

## 1. ภาพรวมสถาปัตยกรรม

```
┌────────────────────────────────────────────────────────────────────┐
│                         MTSecurity Backend                          │
│                                                                      │
│  RTSP/USB → CameraThread ──┬─→ frame_buffer  → AIPipeline          │
│                              ├─→ hires_buffer  → Snapshot/Clip      │
│                              └─→ stream_buffer → MJPEG /stream      │
│                                                                      │
│  AIPipeline → TRACK_UPDATE ──→ MessageBus                          │
│                                    │                                 │
│                         ┌──────────┼──────────────┐                 │
│                         ▼          ▼               ▼                 │
│                    RuleEngine  WebSocketHub    (other subs)          │
│                         │                                            │
│                  RULE_TRIGGERED                                      │
│                         │                                            │
│                         ▼                                            │
│                   AlertManager                                       │
│                    │    │    └─ create_task(save_clip_deferred)      │
│                    │    └────── create_task(dispatch_notifications)  │
│                    └─ ALERT_FIRED → MessageBus → WebSocketHub       │
│                                                    → Frontend WS     │
└────────────────────────────────────────────────────────────────────┘
```

### Layer สำคัญ

| Layer | ไฟล์หลัก | หน้าที่ |
|---|---|---|
| **Ingestion** | `ingestion/camera_thread.py`, `camera_manager.py` | อ่าน RTSP/USB, encode 3 tier, เขียน buffers |
| **AI** | `ai/pipeline.py`, `ai/inference_engine.py`, `ai/tracker.py` | Inference YOLOv11n, ByteTrack, emit TRACK_UPDATE |
| **Rules** | `rules/rule_engine.py`, `rules/logic_validator.py` | Evaluate rules, cooldown, emit RULE_TRIGGERED |
| **Alerts** | `alerts/alert_manager.py`, `alerts/snapshot.py` | บันทึก Event, Snapshot, Clip, ส่ง notifications |
| **Protocol** | `protocol/message_bus.py`, `protocol/mtp.py` | In-process async priority queue |
| **SSOT** | `ssot/config_service.py`, `ssot/state_registry.py` | Single source of truth สำหรับ config |
| **API** | `api/routers/`, `api/websocket/` | FastAPI REST + WebSocket |

---

## 2. Detection Pipeline

### Flow ทีละขั้น

```
1. CameraThread.run()
   └─ cap.read() → decode frame → encode 3 tier
      ├─ THUMBNAIL (320×180 q60)  → frame_buffer.put(frame)
      ├─ evidence_tier*           → hires_buffer.put(frame)
      └─ stream_tier*             → stream_buffer.put(frame)
                                     ↑ also: clip_buffer.put(frame)

2. AIPipeline._run()  [background thread, ~30 Hz]
   └─ frame_buffer.get(camera_id)
   └─ InferenceEngine.infer() → YOLOv11n detections
   └─ ObjectTracker.update()  → ByteTrack tracks
   └─ bus.publish_nowait(TRACK_UPDATE)

3. RuleEngine._on_track_update()  [async, on MessageBus]
   └─ for each detection × each rule:
      ├─ confidence gate (BUG-020 fix)
      ├─ zone containment check
      ├─ behavior evaluation (intrusion/loitering/crowd/...)
      ├─ cooldown check (BUG-019 fix — expire stale tracks)
      └─ bus.publish(RULE_TRIGGERED)

4. AlertManager._on_rule_triggered()  [async, on MessageBus]
   └─ DB: create Event + Snapshot
   └─ bus.publish(ALERT_FIRED)       ← ทันที, ไม่รอ
   └─ create_task(save_clip_deferred)
   └─ create_task(dispatch_notifications)  ← background (BUG-022 fix)

5. WebSocketHub._on_alert_fired()
   └─ broadcast JSON → ทุก browser ที่เชื่อมต่ออยู่
```

### จุดสำคัญ

- **AIPipeline รันใน thread แยก** — ใช้ `bus.publish_nowait()` (thread-safe via `call_soon_threadsafe`) ห้ามใช้ `await bus.publish()` จาก thread
- **TRACK_UPDATE ส่ง ~30 Hz ต่อกล้อง** — RuleEngine evaluate ทุก frame, cooldown กัน spam
- **ทุกอย่างหลัง TRACK_UPDATE รันบน event loop** — ห้าม block ด้วย sync I/O

---

## 3. MessageBus

### กฎการใช้งาน — สำคัญมาก

```python
# ✅ จาก async context (event loop)
await bus.publish(msg)

# ✅ จาก thread (AIPipeline, CameraThread)
bus.publish_nowait(msg)

# ❌ อย่าใช้ run_coroutine_threadsafe — สร้าง dangling futures
```

### ⚠️ กฎห้ามทำใน Handler

Handler ที่ subscribe กับ bus จะถูกเรียกภายใน `_dispatch_loop` ซึ่งประมวลผล **ทีละ message** การ block handler = block บัสทั้งระบบ

```python
# ❌ อย่า await network call ใน handler โดยตรง
async def _on_something(self, msg):
    await requests.post(...)       # ← block บัส 3-10 วิ!
    await asyncio.sleep(10)        # ← block บัสตลอด!

# ✅ background task สำหรับงานที่ใช้เวลานาน
async def _on_something(self, msg):
    await self._do_quick_db_work()   # < 100ms ตกลงได้
    asyncio.create_task(self._slow_network_task())  # ← background
```

### Priority Queue

| Priority | ค่า | ใช้กับ |
|---|---|---|
| `CRITICAL` | 1 | System shutdown, fatal error |
| `HIGH` | 2 | ALERT_FIRED, RULE_TRIGGERED |
| `NORMAL` | 3 | TRACK_UPDATE, CONFIG_CHANGED |
| `LOW` | 4 | HEALTH_BEAT, analytics |

### TTL

Message มี TTL 30 วินาที (default) — ถ้าบัสช้าเกิน 30 วิ message จะถูก drop ทิ้งโดยไม่มี error เป็น fail-safe ป้องกัน stale data เข้า handler

---

## 4. Cooldown & Track ID System

### โครงสร้าง Cooldown

```python
# key: (rule_id, track_id) → เวลา monotonic ที่ trigger ล่าสุด
_last_trigger: dict[tuple[int, int], float]

# key: track_id → เวลา monotonic ที่ detect ล่าสุด
_track_last_seen: dict[int, float]
```

### กลไก Stale Track Expiry (BUG-019)

**ปัญหา:** ByteTrack มี `MAX_AGE=20 frames` (~1.3 วิ @ 15fps) ก่อน track ตาย ถ้า object ใหม่เข้ามาก่อน track เก่าตาย ByteTrack อาจ assign `track_id` เดิมซ้ำ → object ใหม่ inherit cooldown เก่า → ถูก suppress ผิดๆ

**วิธีแก้:**
```python
def _expire_stale_cooldowns(self, now: float) -> None:
    # ถ้า track ไม่ถูก detect > 3 วิ → ลบ cooldown entries ทิ้ง
    stale_ids = {tid for tid, t in self._track_last_seen.items()
                 if (now - t) > 3.0}
    dead_keys = [k for k in self._last_trigger if k[1] in stale_ids]
    for k in dead_keys: del self._last_trigger[k]
    for tid in stale_ids: del self._track_last_seen[tid]
```

เรียกทุก frame ก่อน evaluate rules

### หลายๆ Object ทยอยเข้า Zone

```
object A (track_id=10) → trigger → cooldown(rule, 10) เริ่ม
object B (track_id=11) → คนละ track_id → cooldown(rule, 11) = None → trigger ✅
object C (track_id=12) → คนละ track_id → trigger ✅
object A อีกครั้ง    → cooldown(rule, 10) ยังไม่หมด → suppress ✅ (ตั้งใจ)
```

**ระบบรองรับ multi-object ได้ถูกต้อง** — แต่ละ object มี cooldown แยกกัน

### Confidence Threshold (BUG-020)

```python
# ลำดับ priority การ fallback:
conf_threshold = rule_cfg.get("confidence_threshold") or self._default_confidence
# 1. ค่า per-rule จาก DB (ตั้งใน Rule form)
# 2. _default_confidence จาก system_settings (Admin ตั้งได้ live)
# 3. hardcode 0.6 (ถ้า DB ไม่มีค่า)
```

---

## 5. Video Evidence — Snapshot & Clip

### Three-Buffer Architecture

```
raw frame (RTSP/USB)
  ├─ encode THUMBNAIL (320×180 q60) → frame_buffer  → AI Pipeline
  ├─ encode evidence_tier*          → hires_buffer  → Snapshot + Clip
  └─ encode stream_tier*            → stream_buffer → MJPEG Live
                                                  + clip_buffer (ring)
```

`*` ปรับได้ใน Settings

### Snapshot Flow

```python
# AlertManager._on_rule_triggered()
frame = (hires_buffer or frame_buffer).get(camera_id)  # prefer hi-res
img = cv2.imdecode(frame.data, IMREAD_COLOR)
path = save_snapshot(img, detections, ...)
event.snapshot_path = path.name
```

### Clip — Pre+Post Event Design

**หลักการ:** ring buffer เก็บ footage ต่อเนื่อง → เมื่อ trigger อย่าบันทึกทันที → รอ `post_seconds` ก่อน → buffer จะมีทั้ง pre และ post footage ให้ตัดได้

```
timeline:  ──────[pre 5s]──[DETECT]──[post 10s]──→
buffer:    ████████████████  ← ถ่ายต่อเนื่องทุก frame
                              ↑ trigger เกิดที่นี่
                                              ↑ บันทึก clip ตรงนี้
                                                (sleep post_seconds แล้วค่อย save)
```

```python
# AlertManager._save_clip_deferred()
await asyncio.sleep(post_seconds)          # รอ buffer สะสม post-event
loop = asyncio.get_running_loop()
clip_path = await loop.run_in_executor(    # blocking OpenCV ใน thread
    None, lambda: clip_buffer.save_clip(
        camera_id, event_id, clip_dir,
        pre_seconds=pre_secs,              # ตัดเอาแค่ tail pre+post
    )
)
```

```python
# ClipBuffer.save_clip()
if pre_seconds > 0:
    max_frames = int(pre_seconds * fps)
    frames = frames[-max_frames:]          # tail = [pre + post footage]
```

### Ring Buffer Size

```python
# app.py
clip_buffer = ClipBuffer(max_frames=600)  # 600 frames ≈ 40 วิ @ 15fps
```

ต้องใหญ่พอรองรับ `pre + post` ที่ Admin ตั้งสูงสุด (30+30=60 วิ ต้อง max_frames=900)

### FFmpeg Post-processing

หลัง OpenCV เขียน mp4v (moov ท้ายไฟล์) → FFmpeg remux + `-movflags +faststart` ให้ moov อยู่หน้าไฟล์ → browser เล่นได้และแสดง duration ถูกต้อง

---

## 6. WebSocket Real-time Layer

### Connection Lifecycle

```python
# router.py — ถูกต้องแล้ว (BUG-021 fix)
try:
    while True:
        raw = await websocket.receive_text()
        await hub.handle_message(client, raw)
except WebSocketDisconnect:
    pass
except Exception as exc:
    logger.debug("WS connection dropped: %s", exc)
finally:
    await hub.disconnect(client)  # ← guaranteed cleanup
```

### ⚠️ Pitfall: จับแค่ WebSocketDisconnect ไม่พอ

Browser ปิด tab / network drop จะ throw `ConnectionResetError` หรือ `RuntimeError("Cannot call receive")` ไม่ใช่ `WebSocketDisconnect` → ต้องใช้ `finally` เสมอ

### Message Types จาก Hub

| type | เมื่อ | payload |
|---|---|---|
| `alert_fired` | ALERT_FIRED บัส | `{alert_id, rule_name, camera_id, behavior, severity, snapshot_url}` |
| `frame_ready` | FRAME_READY บัส | `{camera_id, ...}` |
| `track_update` | TRACK_UPDATE บัส | `{camera_id, detections: [...]}` |
| `camera_status` | CAMERA_STATUS บัส | `{camera_id, state, error_msg}` |

### Subscribe Filter

Client ส่ง `{"type": "subscribe", "camera_ids": [1, 2]}` → hub ส่งเฉพาะ camera ที่ระบุ (ยกเว้น `alert_fired` ที่ส่งทุก client เสมอ)

---

## 7. Live-reload Settings Pattern

### Pattern มาตรฐาน

ทุก setting ที่มีผลทันทีใช้ pattern เดียวกัน:

```
Admin กด บันทึก
  → PATCH /api/v1/system/settings
  → system.py: บันทึก DB + publish CONFIG_CHANGED
  → subscriber รับ → อัปเดต in-memory ทันที
```

```python
# system.py — publish หลัง DB commit
if body.key in _LIVE_RELOAD_KEYS:
    await bus.publish(MTPMessage(
        msg_type=MTPMsgType.CONFIG_CHANGED,
        payload={"scope": "system_setting", "key": body.key, "value": str(cast)},
        source="system_router",
    ))
```

```python
# subscriber (เช่น RuleEngine)
async def _on_config_changed(self, msg):
    if msg.payload.get("scope") == "system_setting":
        key = msg.payload.get("key")
        if key == "default_cooldown_seconds":
            self._default_cooldown = int(msg.payload["value"])
        return
    # ... handle rule/zone/camera scope
```

### Settings ที่ Live-reload ได้

| Setting | Subscriber | ผล |
|---|---|---|
| `stream_tier` | CameraManager | restart camera threads (~2-3 วิ) |
| `evidence_tier` | CameraManager | restart camera threads (~2-3 วิ) |
| `default_cooldown_seconds` | RuleEngine | มีผลทันที frame ถัดไป |
| `default_confidence_threshold` | RuleEngine | มีผลทันที frame ถัดไป |
| `clip_crf`, `clip_pre_seconds`, `clip_post_seconds` | อ่าน DB ต่อ alert | มีผล clip ถัดไป |

### เพิ่ม Live-reload Setting ใหม่

1. เพิ่มใน `_ALLOWED` ใน `system.py`
2. เพิ่ม key ใน `_LIVE_RELOAD_KEYS` ใน `system.py`
3. handle ใน `_on_config_changed()` ของ subscriber ที่เกี่ยวข้อง
4. เพิ่ม UI control ใน `SettingsView.vue`

---

## 8. ปัญหาที่พบบ่อย (Pitfalls)

### P-01 — Object ใหม่ไม่ trigger alert หลัง object เก่าเพิ่งออก

**สาเหตุ:** Track ID reuse (ByteTrack MAX_AGE) → object ใหม่ inherit cooldown เก่า  
**ตรวจสอบ:** log `"Rule X evaluation: SUPPRESSED (cooldown)"` + track_id ซ้ำ  
**แก้ไข:** มีแล้ว (BUG-019) — `_expire_stale_cooldowns()` ทุก 3 วิ  
**ปรับได้:** `self._stale_track_seconds` ใน `rule_engine.py`

---

### P-02 — ระบบนิ่งไม่ตอบสนองหลัง alert ในช่วง 3–10 วิ

**สาเหตุ:** Notification dispatch (LINE/Discord) block MessageBus ทั้งระบบ  
**ตรวจสอบ:** log `"notifications sent via"` ตามหลัง alert นานเกิน 3 วิ  
**แก้ไข:** มีแล้ว (BUG-022) — notifications รันใน `asyncio.create_task`  
**ระวัง:** อย่านำ network call กลับไป await inline ใน handler อีก

---

### P-03 — WebSocket ECONNRESET / client ค้างใน hub

**สาเหตุ:** `except WebSocketDisconnect` ไม่จับ `ConnectionResetError`  
**ตรวจสอบ:** log `"WS client connected"` เพิ่มขึ้นเรื่อยๆ โดยไม่มี disconnect  
**แก้ไข:** มีแล้ว (BUG-021) — ใช้ `finally: await hub.disconnect(client)`  
**กฎ:** WebSocket endpoint ต้องมี `finally` block เสมอ

---

### P-04 — Confidence threshold ตั้งไว้แต่ไม่มีผล

**สาเหตุ:** cache ค่าไว้ใน `_rules` แต่ลืม apply ก่อน evaluate  
**ตรวจสอบ:** alert ยิงแม้ confidence ต่ำกว่าที่ตั้ง  
**แก้ไข:** มีแล้ว (BUG-020) — confidence gate ก่อน `_TrackProxy`  
**pattern:** ทุก rule setting ที่ cache ต้องถูก apply ใน evaluate loop

---

### P-05 — Clip ไม่มีภาพก่อนเกิดเหตุ (เริ่มจากจุด detect)

**สาเหตุ:** บันทึก clip ทันทีหลัง detect — buffer มีแค่ pre-footage  
**แก้ไข:** มีแล้ว (FEAT-012) — `sleep(post_seconds)` ก่อน `save_clip(pre_seconds=...)`  
**ระวัง:** ring buffer ต้องใหญ่พอ `max_frames >= (pre+post) × fps`

---

### P-06 — Video Clip เล่นใน browser แล้ว duration แสดง 0:00

**สาเหตุ:** OpenCV + mp4v codec เขียน moov atom ท้ายไฟล์ (browser ต้องดาวน์โหลดทั้งหมดก่อน)  
**แก้ไข:** มีแล้ว — FFmpeg `-movflags +faststart` ย้าย moov ไปหน้าไฟล์  
**ระวัง:** FFmpeg ต้องติดตั้งและ `FFMPEG_PATH` ตั้งค่าใน `.env`

---

### P-07 — Evidence Tier เปลี่ยนแล้วกล้องยังใช้ค่าเก่า

**สาเหตุ:** `CameraThread` อ่าน tier ตอน startup เท่านั้น  
**แก้ไข:** มีแล้ว (FEAT-010) — `CONFIG_CHANGED` trigger `_restart_all_cameras()`  
**ผลข้างเคียง:** กล้อง offline ~2-3 วิ ระหว่าง restart (แจ้ง user ใน UI แล้ว)

---

### P-08 — DateTime แสดงผิด (ช้าไป 7 ชั่วโมง)

**สาเหตุ:** SQLite เก็บ datetime ไม่มี timezone → Pydantic serialize เป็น naive string → browser ตีความเป็น local time  
**แก้ไข:** มีแล้ว (BUG-018) — `@field_validator` attach UTC + frontend `parseUtcIso()` append `Z`  
**กฎ:** datetime ทุกตัวในระบบนี้เป็น UTC เสมอ — ใช้ `datetime.now(timezone.utc)`

---

### P-09 — Rule ว่างเปล่า trigger alert ทุก detection

**สาเหตุ:** vacuous truth: `AND([]) = True`  
**แก้ไข:** มีแล้ว (BUG-002) — `if not conditions: return False` ใน logic_validator  
**กฎ:** ทุก operator ที่ accept list of conditions ต้องมี empty guard

---

### P-10 — TRACK_UPDATE ส่งจาก thread แต่ใช้ `await bus.publish()`

**สาเหตุ:** AIPipeline รันใน daemon thread ไม่ใช่ event loop  
**อาการ:** `RuntimeError: no running event loop` หรือ deadlock  
**แก้ไข:** ใช้ `bus.publish_nowait(msg)` เสมอจาก thread context

---

## 9. Debugging Guide

### ตรวจสอบ Detection Pipeline

```bash
# 1. ตรวจว่า AI กำลัง detect อยู่หรือเปล่า
grep "TRACK_UPDATE\|AIPipeline" backend.log | tail -20

# 2. ตรวจว่า RuleEngine evaluate อยู่หรือเปล่า
grep "Rule.*evaluation\|SUPPRESSED\|TRIGGERED" backend.log | tail -20

# 3. ตรวจ cooldown
grep "cooldown" backend.log | tail -20

# 4. ตรวจ AlertManager
grep "Event.*persisted\|Alert fired\|notifications sent" backend.log | tail -20
```

### ตรวจสอบ MessageBus

```python
# ดู queue size จาก health endpoint
GET /api/v1/health  # ดู bus queue ใน response

# หรือ log โดยตรง
logger.info("Bus queue: %d", bus.queue_size)
```

### ตรวจสอบ WebSocket

```javascript
// Browser console
const ws = new WebSocket('ws://localhost:8000/api/v1/ws?token=...')
ws.onmessage = e => console.log(JSON.parse(e.data))
```

### ตรวจสอบ Clip Buffer

```python
# log จำนวน frame ใน buffer
logger.info("ClipBuffer frames for cam %d: %d", cam_id, len(clip_buffer.snapshot(cam_id)))
```

### Log Levels

| Logger | ข้อมูล |
|---|---|
| `mtsecurity.app` | startup/shutdown lifecycle |
| `rules.rule_engine` | evaluate, trigger, suppress |
| `alerts.alert_manager` | event persist, snapshot, clip, notify |
| `ingestion.clip_buffer` | frame count, save path |
| `api.websocket.router` | connect/disconnect |
| `protocol.message_bus` | queue full, expired message |

---

## 10. System Settings — ตารางอ้างอิง

| Key | Type | ช่วง | Default | Live-reload | ความหมาย |
|---|---|---|---|---|---|
| `jwt_access_token_expire_minutes` | int | 5–1440 | 60 | ❌ token ใหม่เท่านั้น | อายุ access token |
| `jwt_refresh_token_expire_days` | int | 1–90 | 7 | ❌ token ใหม่เท่านั้น | อายุ refresh token |
| `default_cooldown_seconds` | int | 10–600 | 60 | ✅ ทันที | ห่างเท่าไหร่ก่อน object เดิม trigger ซ้ำ |
| `default_confidence_threshold` | int (%) | 10–95 | 60 | ✅ ทันที | AI ต้องมั่นใจขั้นต่ำ |
| `stream_tier` | str | THUMBNAIL/MONITOR/DETAIL | MONITOR | ✅ restart ~3s | ความละเอียด MJPEG live stream |
| `evidence_tier` | str | MONITOR/DETAIL/EVIDENCE | DETAIL | ✅ restart ~3s | ความละเอียด Snapshot + Clip |
| `clip_crf` | int | 18–28 | 23 | ✅ clip ถัดไป | คุณภาพวิดีโอ (18=คมสุด ไฟล์ใหญ่) |
| `clip_pre_seconds` | int | 2–30 | 5 | ✅ clip ถัดไป | วินาทีก่อน detect ใน clip |
| `clip_post_seconds` | int | 2–30 | 10 | ✅ clip ถัดไป | วินาทีหลัง detect ใน clip |

---

## 11. การ์ดสรุป Bug Index

| ID | อาการสั้น | สาเหตุหลัก | สถานะ |
|---|---|---|---|
| BUG-001 | Loitering alert แสดง behavior ผิด | `rule.behavior` ≠ behavior ใน logic tree | ✅ Fixed |
| BUG-002 | Empty rule trigger ทุก detection | Vacuous truth `AND([]) = True` | ✅ Fixed |
| BUG-003 | Behavior params ใน logic mode ใช้ร่วมกัน | `behavior_params` เป็น top-level field เดียว | ✅ Fixed |
| BUG-004–016 | (ดู BUGFIX_LOG.md) | — | ✅ Fixed |
| BUG-017 | Live stream ไม่ชัด | frame_buffer เก็บแค่ THUMBNAIL tier | ✅ Fixed |
| BUG-018 | เวลา event ผิด 7 ชั่วโมง | SQLite naive datetime + browser local TZ | ✅ Fixed |
| BUG-019 | Object ใหม่ถูก suppress หลัง object เก่าออก | ByteTrack track_id reuse | ✅ Fixed |
| BUG-020 | Confidence threshold ไม่มีผล | cache แต่ไม่ได้ apply ใน evaluate loop | ✅ Fixed |
| BUG-021 | WebSocket ECONNRESET / dead client ค้าง | `except WebSocketDisconnect` ไม่ครอบทุกกรณี | ✅ Fixed |
| BUG-022 | ระบบนิ่ง 3–10 วิ หลัง alert | notification dispatch block MessageBus | ✅ Fixed |

| ID | Feature | สถานะ |
|---|---|---|
| FEAT-010 | Live-reload stream/evidence tier ไม่ต้อง restart server | ✅ Done |
| FEAT-011 | Admin ตั้งค่า cooldown + confidence threshold ได้ live | ✅ Done |
| FEAT-012 | Clip บันทึกก่อน+หลัง detect, Admin ตั้งค่าได้ | ✅ Done |

---

*อัปเดตล่าสุด: 2026-05-19 — ครอบคลุม BUG-001 ถึง BUG-022, FEAT-010 ถึง FEAT-012*
