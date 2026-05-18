# MTSecurity — Bug Fix Log

> บันทึกการแก้ไข bug ทั้งหมด เรียงตามวันที่แก้ไข  
> รูปแบบ: **อาการ → สาเหตุ → วิธีแก้ → ไฟล์ที่แก้**

---

## 2026-05-16

---

### BUG-001 — Loitering alert แสดง behavior ผิด ("intrusion" แทนที่จะเป็น "loitering")

**Severity:** Medium  
**Component:** Backend — Rule Engine

**อาการ:**  
Alert ที่ trigger จาก rule loitering แสดง `behavior = "intrusion"` ใน alert log

**สาเหตุ:**  
`rule_engine.py` ใช้ `rule_cfg.get("behavior")` ในการ log และสร้าง alert payload แต่เมื่อใช้ Advanced Logic mode ค่า `rule.behavior` ที่บันทึกใน DB อาจไม่ตรงกับ behavior ที่ประมวลผลจริงใน logic tree (เช่น user ตั้ง behavior หลักเป็น "intrusion" แล้วสร้าง logic tree ที่มี behavior:loitering)

**วิธีแก้:**  
เพิ่ม `_extract_behavior_from_tree()` helper ที่ walk logic tree หา behavior node แรก และใช้ค่านั้น (`behavior_override`) แทน `rule_cfg.get("behavior")` ใน log และ alert payload

**ไฟล์ที่แก้:**
- `backend/rules/rule_engine.py` — `_emit_triggered()` และ `_extract_behavior_from_tree()`

---

### BUG-002 — Vacuous truth: empty AND tree trigger ทุก detection

**Severity:** Critical (Security)  
**Component:** Backend — Logic Validator

**อาการ:**  
Rule ที่มี Advanced Logic tree ว่างเปล่า (ไม่มี conditions) trigger alert ทุกครั้งที่มี detection ในกล้อง

**สาเหตุ:**  
Standard boolean logic: `AND([]) = True` (vacuous truth) — `logic_validator.py` ไม่มี guard สำหรับ empty conditions ทำให้ AND/OR/NOT ว่างล้วน return True ซึ่งหมายความว่า rule ที่ยังไม่ได้กำหนด conditions จะยิง alert ตลอดเวลา

**วิธีแก้:**  
เพิ่ม `if not conditions: return False` ใน AND, OR, และ NOT operator ก่อน evaluate — empty conditions = ยังไม่มี intent ที่จะ trigger

```python
if operator == "AND":
    if not conditions:
        return False   # ← เพิ่ม
    ...
if operator == "NOT":
    if not conditions:
        return False   # ← เดิมเป็น True (bug!)
    ...
```

**ไฟล์ที่แก้:**
- `backend/rules/logic_validator.py` — `evaluate()`

---

### BUG-003 — Behavior params ใน Advanced Logic mode ไม่สามารถกำหนดต่อ node ได้

**Severity:** High  
**Component:** Backend + Frontend — Logic Builder

**อาการ:**  
เมื่อใช้ Advanced Logic mode ที่มี behavior node หลายตัว (เช่น loitering dwell=20s + crowd_density max=5) params ของทุก node ใช้ค่า top-level `behavior_params` ร่วมกัน ทำให้ตั้งค่าแยกกันไม่ได้

**สาเหตุ:**  
สถาปัตยกรรมเดิม: `behavior_params` เป็น field เดียวระดับ rule ซึ่งทุก behavior node อ่านร่วมกัน ไม่รองรับกรณีที่ logic tree มี behavior node หลายตัวที่ต้องการ params ต่างกัน

**วิธีแก้:**  
เปลี่ยนสถาปัตยกรรมให้ behavior-specific params ฝังอยู่ภายใน `node.params` ของแต่ละ behavior node ใน logic tree โดยตรง

- **Backend:** `logic_validator.py` — สร้าง `node_bp` จาก `params` ของ node (ยกเว้น reserved keys `type`, `zone_id`) และ assign เป็น `behavior_params` ให้แต่ละ behavior โดยเฉพาะ
- **Frontend:** `RuleLogicBuilder.vue` — เพิ่ม inline param inputs สำหรับทุก behavior (11 behaviors) ภายใน behavior node block
- **Frontend:** `ZonesView.vue` — ส่ง `behavior_params: null` เมื่อใช้ Advanced Logic mode

**ไฟล์ที่แก้:**
- `backend/rules/logic_validator.py` — `_evaluate_node()` behavior case
- `frontend/src/components/RuleLogicBuilder.vue` — behavior node params UI
- `frontend/src/views/ZonesView.vue` — `submitRule()`

---

### BUG-004 — Dwell cascade ใน Advanced Logic mode ใช้ค่า default behavior แทนค่าที่ตั้งใน node

**Severity:** High  
**Component:** Backend — Logic Validator

**อาการ:**  
Loitering behavior node ใน Advanced Logic tree ที่ตั้ง `dwell_threshold_seconds=45s` ทำงานด้วย 30s (default ของ loitering behavior) แทน

**สาเหตุ:**  
`logic_validator.py` ไม่ดึง `dwell_threshold_seconds` ออกจาก `node_bp` มาวางที่ top-level `eval_config` ก่อนที่ loitering behavior จะอ่าน — loitering อ่าน dwell จาก `config.get("dwell_threshold_seconds")` (top-level) ไม่ใช่จาก `behavior_params`

**วิธีแก้:**  
ใช้ `.pop()` ดึง `dwell_threshold_seconds` ออกจาก `node_bp` แล้ว override ที่ top-level ก่อน assign `behavior_params` — cascade priority: node param > rule-level > behavior default

```python
if "dwell_threshold_seconds" in node_bp:
    eval_config["dwell_threshold_seconds"] = node_bp.pop("dwell_threshold_seconds")
```

ใช้ `.pop()` เพื่อไม่ให้ dwell ไปอยู่ใน `behavior_params` ด้วย (loitering อ่านจาก top-level เท่านั้น)

**ไฟล์ที่แก้:**
- `backend/rules/logic_validator.py` — `_evaluate_node()` behavior case

---

### BUG-005 — `onBehaviorTypeChange` อ่าน type เก่า (stale value) เพราะ `@change` fires ก่อน v-model update

**Severity:** High  
**Component:** Frontend — Rule Logic Builder

**อาการ:**  
เมื่อเปลี่ยน behavior type dropdown ใน logic builder (เช่น loitering → running) behavior params ที่แสดงยังคงเป็น params ของ type เก่า หรือ params ไม่ reset ให้ตรงกับ type ใหม่

**สาเหตุ:**  
Vue's `@change` event fires ก่อน `v-model` update — ดังนั้น `onBehaviorTypeChange(cond)` ที่อ่าน `cond.params.type` จะยังได้ค่า type เก่า แล้วสร้าง default params ผิด type

**วิธีแก้:**  
เปลี่ยน `v-model` เป็น `:value` + `@change` ที่ส่ง `e.target.value` (new value) เป็น argument โดยตรง

```html
<!-- เดิม -->
<select v-model="cond.params!.type" @change="onBehaviorTypeChange(cond)">

<!-- ใหม่ -->
<select :value="cond.params!.type"
  @change="e => onBehaviorTypeChange(cond, (e.target as HTMLSelectElement).value)">
```

```typescript
// เดิม
function onBehaviorTypeChange(cond: LogicNode) {
  cond.params = { type: cond.params!.type }  // อ่าน type เก่า!

// ใหม่
function onBehaviorTypeChange(cond: LogicNode, newType: string) {
  cond.params = { type: newType }  // ใช้ค่าจาก event โดยตรง
```

**ไฟล์ที่แก้:**
- `frontend/src/components/RuleLogicBuilder.vue` — behavior type select + `onBehaviorTypeChange()`

---

### BUG-006 — Basic/Advanced Logic mode conflict: stale behavior ค้างจากโหมดก่อนหน้า

**Severity:** High  
**Component:** Frontend — Zones View

**อาการ:**  
เมื่อกรอก behavior A ใน Basic mode แล้วสลับไป Advanced Logic mode แล้วบันทึก — `effectiveBehavior` fallback อาจใช้ค่าเก่าจาก Basic mode ถ้า logic tree ว่างอยู่ ทำให้ DB บันทึก behavior ที่ไม่ตรงกับสิ่งที่ user ต้องการ

**สาเหตุ:**  
ไม่มีการ reset state เมื่อสลับโหมด — `ruleForm.behavior` ยังคงค่าเดิมจาก Basic mode เมื่อสลับไป Advanced

**วิธีแก้:**  
เพิ่ม `watch(useAdvancedLogic)` ที่ reset `ruleForm.behavior` และ `behaviorParams` เมื่อสลับกลับไป Basic mode เพิ่ม validation ที่ block submission เมื่อ Advanced Logic tree ว่าง

```typescript
watch(useAdvancedLogic, (isAdvanced) => {
  if (!isAdvanced) {
    ruleForm.value.behavior = '' as any  // บังคับให้ user เลือกใหม่
    behaviorParams.value = {}
  }
})
```

**ไฟล์ที่แก้:**
- `frontend/src/views/ZonesView.vue` — `watch(useAdvancedLogic)`, `submitRule()` validation

---

### BUG-007 — Rule card summary แสดง dwell/max_persons ผิดสำหรับ Advanced Logic rules

**Severity:** Medium  
**Component:** Frontend — Zones View

**อาการ:**  
Rule card ใน Zones page แสดง `dw 30s` หรือ `max 5 persons` แม้ rule จะตั้งค่าไว้ต่างออกไปใน Advanced Logic tree (เช่น loitering node มี `dwell_threshold_seconds: 45`)

**สาเหตุ:**  
Card summary อ่านจาก `rule.dwell_threshold_seconds` และ `rule.behavior_params?.max_persons` ซึ่งเป็น `null` สำหรับ Advanced Logic rules — fallback ไปใช้ค่า default แทน

**วิธีแก้:**  
เพิ่ม helper functions ที่ walk logic tree หาค่าที่ถูกต้อง

```typescript
function findBehaviorNode(node: any, types: string[]): any { ... }
function ruleDwellSeconds(rule: RuleRead): number {
  if (rule.logic) {
    const node = findBehaviorNode(rule.logic, ['loitering', 'abandoned_object'])
    if (node?.params?.dwell_threshold_seconds) return node.params.dwell_threshold_seconds
  }
  return rule.dwell_threshold_seconds
}
function ruleMaxPersons(rule: RuleRead): number { ... }
```

**ไฟล์ที่แก้:**
- `frontend/src/views/ZonesView.vue` — `findBehaviorNode()`, `ruleDwellSeconds()`, `ruleMaxPersons()`

---

### BUG-008 — `movement_threshold` ของ abandoned_object hardcoded ไม่อ่านจาก behavior_params

**Severity:** Medium  
**Component:** Backend — Abandoned Object Behavior

**อาการ:**  
ผู้ใช้ตั้งค่า `movement_threshold` ใน UI แต่ backend ใช้ค่า hardcoded `0.02` เสมอ

**สาเหตุ:**  
`abandoned_object.py` อ่าน `movement_threshold` จาก top-level config (`config.get("movement_threshold")`) แทนที่จะอ่านจาก `config.get("behavior_params")` ที่เป็นที่เก็บ behavior-specific params

**วิธีแก้:**
```python
# เดิม
move_thresh = config.get("movement_threshold", _MOVEMENT_THRESHOLD)

# ใหม่
bp: dict = config.get("behavior_params") or {}
move_thresh = bp.get("movement_threshold", _MOVEMENT_THRESHOLD)
```

**ไฟล์ที่แก้:**
- `backend/rules/behaviors/abandoned_object.py` — `evaluate()`

---

### BUG-009 — Abandoned object behavior ไม่ trigger เพราะ track_id เปลี่ยนทุกครั้งที่ confidence กระพริบ

**Severity:** Critical (Functional)  
**Component:** Backend — Abandoned Object Behavior + Tracker

**อาการ:**  
วางวัตถุนิ่งๆ (กระเป๋า, กล่อง) ไว้ใน zone — behavior ไม่ trigger แม้จะรอนานกว่า dwell threshold

**สาเหตุ:**  
วัตถุที่อยู่นิ่งๆ ทำให้ AI model มี confidence กระพริบ (object บางเฟรมไม่ถูก detect) เมื่อ detection หายไป `_MAX_AGE = 5` frames tracker จะลบ track นั้น เมื่อ detect ได้ใหม่จะได้ track_id ใหม่ — dwell timer ที่ key ด้วย `(rule_id, track_id)` จะ reset เป็น 0 ทุกครั้ง ทำให้ไม่มีวันสะสมถึง threshold

```
TRK-100 → dwell 45s → confidence drop → track ตาย
TRK-101 (new) → dwell 0s ← reset!
```

**วิธีแก้:**  
สองส่วนพร้อมกัน:

1. **Tracker:** เพิ่ม `_MAX_AGE: 5 → 20` frames (~2s at 10fps) ให้ stationary track อยู่ได้นานขึ้นโดยไม่ต้องมี detection ต่อเนื่อง

2. **Abandoned Object:** เปลี่ยน dwell key จาก `(rule_id, track_id)` เป็น **spatial grid cell** `(rule_id, gx, gy)` — quantize centroid ด้วย grid 4% ของ frame — detection ใหม่ที่ตกใน grid cell เดิมจะ inherit dwell time โดยอัตโนมัติ ไม่ว่า track_id จะเปลี่ยนกี่ครั้ง

```python
def _pos_key(self, rule_id, centroid, grid=0.04):
    cx, cy = centroid
    return (rule_id, int(cx / grid), int(cy / grid))

# pos_state: (rule_id, gx, gy) → (first_seen, last_seen, anchor)
```

Ghost TTL = `max(dwell_threshold × 2, 30s)` ป้องกัน cell ค้างหลัง object ออกไปแล้ว

**ไฟล์ที่แก้:**
- `backend/ai/tracker.py` — `_MAX_AGE: 5 → 20`
- `backend/rules/behaviors/abandoned_object.py` — refactor ทั้ง class ให้ใช้ position-based dwell

---

### BUG-010 — FPS แสดง 0.0 ตลอดเวลาแม้กล้องทำงานปกติ

**Severity:** Medium  
**Component:** Backend — Camera Thread + Frontend

**อาการ:**  
Pilot View และ Cameras View แสดง `FPS: 0.0` ตลอดเวลา ไม่ขยับแม้กล้องส่งภาพปกติ

**สาเหตุ:**  
`camera_thread.py` ส่ง `FRAME_READY` payload ที่มีแค่ `{camera_id, width, height}` — ไม่มี field `fps` Frontend (`system.ts`) อ่าน `msg.data.fps ?? 0` จึงได้ 0 ตลอด

**วิธีแก้:**  
คำนวณ fps จริงใน `camera_thread.py` ด้วย Exponential Moving Average (EMA, α=0.2) จากเวลาระหว่าง frame แล้วใส่ใน payload

```python
# ใน _process_frame():
now = time.monotonic()
if self._fps_last_time > 0:
    interval = now - self._fps_last_time
    instant_fps = 1.0 / interval if interval > 0 else 0.0
    self._fps_ema = 0.2 * instant_fps + 0.8 * self._fps_ema
self._fps_last_time = now

payload = {
    "camera_id": self.camera_id,
    "width": w, "height": h,
    "fps": round(self._fps_ema, 1),   # ← เพิ่ม
}
```

EMA ให้ค่า fps เรียบ ไม่กระพริบตามแต่ละ frame interval

**ไฟล์ที่แก้:**
- `backend/ingestion/camera_thread.py` — `__init__()` (เพิ่ม `_fps_ema`, `_fps_last_time`) + `_process_frame()`

---

---

## 2026-05-17

---

### FEAT-001 — User Management UI (UsersView)

**Component:** Frontend — User Management  

**เพิ่ม:**
- `frontend/src/views/UsersView.vue` — หน้าจัดการผู้ใช้ (SUPERADMIN/ADMIN เท่านั้น)
  - ตาราง username, display name, role badge, camera scope, สถานะ, วันที่สร้าง
  - Add user modal — username/password/role/display_name/camera_scope
  - Edit user — display_name, is_active, camera_scope
  - Delete user พร้อม confirmation dialog
- `frontend/src/api/client.ts` — เพิ่ม `usersApi`, `UserCreate`, `UserUpdate` interfaces
- `frontend/src/router/index.ts` — `/users` route พร้อม role guard
- `frontend/src/components/AppLayout.vue` — Users nav link (ซ่อนอัตโนมัติถ้าไม่ใช่ ADMIN+)

---

### FEAT-002 — Self-Service Change Password

**Component:** Backend + Frontend — Auth

**เพิ่ม:**
- `backend/api/routers/users.py` — `POST /users/me/change-password`
  - verify bcrypt current_password
  - validate policy (min 8 chars, uppercase, lowercase, digit)
  - return 204 No Content
- `frontend/src/views/SettingsView.vue` — ฟอร์มเปลี่ยนรหัสผ่านในแท็บ บัญชีผู้ใช้

---

### FEAT-003 — Video Clip Recording

**Component:** Backend + Frontend — Alert Pipeline

**สิ่งที่เพิ่ม:**

**Backend:**
- `backend/ingestion/clip_buffer.py` (NEW) — Thread-safe JPEG ring buffer per camera
  - `deque(maxlen=150)` ≈ 10 วินาทีที่ 15 fps
  - `save_clip()` → decode JPEG frames → cv2.VideoWriter → MP4
- `backend/ingestion/camera_thread.py` — รับ `clip_buffer` param, feed ทุก frame ที่ decode ได้
- `backend/ingestion/camera_manager.py` — สร้างและส่ง `ClipBuffer` ไปยัง CameraThread ทุกตัว
- `backend/alerts/alert_manager.py` — เรียก `save_clip()` หลัง trigger, set `event.clip_path`, สร้าง `clip_url`
- `backend/api/routers/events.py` — แก้ `_to_read()` ให้ build `clip_url` จาก `clip_path`, เพิ่ม `GET /events/{id}/clip`
- `backend/api/app.py` — สร้าง `ClipBuffer(max_frames=150)`, ส่งให้ CameraManager และ AlertManager

**Frontend:**
- `frontend/src/views/EventsView.vue` — ปุ่ม ▶ ถ้ามี `clip_url`, เปิด video modal player พร้อม native `<video>`

**Data flow:**
```
CameraThread → ClipBuffer.put(frame)  [every frame, ring-buffer keeps last 150]
                    ↓  (when alert fires)
AlertManager → ClipBuffer.save_clip() → MP4 file → event.clip_path
                    ↓
GET /events/{id}/clip → FileResponse(video/mp4)
                    ↓
EventsView → <video> player modal
```

---

## สรุปไฟล์ที่แก้ไขทั้งหมด

| ไฟล์ | Bug/Feature ที่เกี่ยวข้อง |
|------|-----------------|
| `backend/rules/rule_engine.py` | BUG-001 |
| `backend/rules/logic_validator.py` | BUG-002, BUG-004 |
| `backend/rules/behaviors/abandoned_object.py` | BUG-008, BUG-009 |
| `backend/ai/tracker.py` | BUG-009 |
| `backend/ingestion/camera_thread.py` | BUG-010, FEAT-003 |
| `backend/ingestion/camera_manager.py` | FEAT-003 |
| `backend/ingestion/clip_buffer.py` | BUG-011, FEAT-003 (NEW) |
| `backend/alerts/alert_manager.py` | BUG-011, FEAT-003 |
| `backend/config.py` | BUG-011 |
| `backend/api/routers/events.py` | FEAT-003, FEAT-004 |
| `backend/api/routers/cameras.py` | BUG-015, FEAT-005, FEAT-006 |
| `backend/api/routers/zones.py` | FEAT-006 (NEW endpoints) |
| `backend/api/routers/rules.py` | FEAT-006 (NEW endpoints) |
| `backend/api/routers/users.py` | FEAT-002 |
| `backend/api/deps.py` | BUG-015 |
| `backend/api/middleware/audit.py` | BUG-015 |
| `backend/auth/permissions.py` | FEAT-004 |
| `backend/schemas/event.py` | FEAT-004 |
| `backend/api/app.py` | BUG-011, FEAT-003 |
| `backend/.env` | BUG-011 |
| `frontend/src/components/RuleLogicBuilder.vue` | BUG-003, BUG-005 |
| `frontend/src/views/ZonesView.vue` | BUG-003, BUG-006, BUG-007, FEAT-006 |
| `frontend/src/views/UsersView.vue` | FEAT-001 (NEW) |
| `frontend/src/views/SettingsView.vue` | FEAT-002 |
| `frontend/src/views/EventsView.vue` | BUG-012, BUG-013, BUG-014, FEAT-003, FEAT-004 |
| `frontend/src/stores/cameras.ts` | FEAT-005 |
| `frontend/src/stores/zones.ts` | FEAT-006 |
| `frontend/src/stores/toast.ts` | BUG-014 |
| `frontend/src/api/client.ts` | FEAT-001, FEAT-004, FEAT-005, FEAT-006 |
| `frontend/src/router/index.ts` | BUG-013, FEAT-001 |
| `backend/models/system_setting.py` | FEAT-007 (NEW) |
| `backend/api/routers/system.py` | FEAT-007, FEAT-009, BUG-017, FEAT-010 |
| `frontend/src/components/AppLayout.vue` | FEAT-001, FEAT-008 |
| `backend/ingestion/clip_buffer.py` | FEAT-009 |
| `backend/ingestion/camera_thread.py` | FEAT-009, BUG-017 |
| `backend/ingestion/camera_manager.py` | FEAT-009, BUG-017, FEAT-010 |
| `backend/alerts/alert_manager.py` | FEAT-009 |
| `backend/api/app.py` | FEAT-009, BUG-017 |
| `backend/schemas/event.py` | BUG-018 |
| `frontend/src/utils/time.ts` | BUG-018 (NEW) |
| `frontend/src/views/EventsView.vue` | BUG-018 |
| `frontend/src/views/DashboardView.vue` | BUG-018 |
| `frontend/src/views/PilotView.vue` | BUG-018 |
| `frontend/src/views/CamerasView.vue` | BUG-018 |

---

### BUG-011 — Video clip เล่นใน browser แสดง 0 วินาที / ไม่ seek ได้

**Severity:** High  
**Component:** Backend — Clip Buffer

**อาการ:**  
เปิด clip ใน browser player แล้วแสดง duration = 0:00 และไม่สามารถ seek ได้ แม้ไฟล์จะมีขนาดปกติ

**สาเหตุ:**  
OpenCV `cv2.VideoWriter` กับ `mp4v` codec เขียน `moov atom` (metadata ที่บอก duration + index) ไว้ที่ **ท้ายไฟล์** แทนต้น Browser ต้องโหลดไฟล์ทั้งหมดก่อนถึงจะรู้ duration และ seek ได้ ซึ่งไม่ทำงานกับ HTTP streaming

**วิธีแก้:**  
หลัง `cv2.VideoWriter` เขียนเสร็จ ให้รัน `ffmpeg -movflags +faststart` เพื่อย้าย `moov atom` ไปต้นไฟล์ พร้อม re-encode เป็น `libx264` และ scale เป็น 854×480 (YouTube 16:9 landscape)

```python
def _apply_faststart(src, ffmpeg_exe, out_width, out_height):
    scale = f"scale={out_width}:{out_height}:force_original_aspect_ratio=decrease"
    pad   = f"pad={out_width}:{out_height}:(ow-iw)/2:(oh-ih)/2"
    subprocess.run([
        ffmpeg_exe, "-y", "-i", str(src),
        "-vf", f"{scale},{pad}",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-movflags", "+faststart",
        str(dst),
    ], check=True, ...)
```

FFmpeg path ผู้ใช้ตั้งได้ใน `.env`:
```
FFMPEG_PATH=D:\libs\ffmpeg\bin\ffmpeg.exe
CLIP_WIDTH=854
CLIP_HEIGHT=480
```

**ไฟล์ที่แก้:**
- `backend/ingestion/clip_buffer.py` — เพิ่ม `_resolve_ffmpeg()`, `_apply_faststart()`, อัพเดต `save_clip()`
- `backend/config.py` — เพิ่ม `ffmpeg_path`, `clip_width`, `clip_height`
- `backend/alerts/alert_manager.py` — ส่ง ffmpeg params ไป `save_clip()`
- `backend/api/app.py` — pass ffmpeg config ไปยัง AlertManager
- `backend/.env` — เพิ่ม `FFMPEG_PATH`, `CLIP_WIDTH`, `CLIP_HEIGHT`

---

### FEAT-004 — Admin Event Deletion (Single + Bulk Purge)

**Component:** Backend + Frontend — Events

**เพิ่ม:**

**Backend:**
- `backend/auth/permissions.py` — เพิ่ม `"events:delete": {Role.SUPERADMIN, Role.ADMIN}`
- `backend/schemas/event.py` — เพิ่ม `EventPurgeRequest`, `EventPurgeResponse`
- `backend/api/routers/events.py`:
  - `DELETE /events/{event_id}` — ลบ snapshot + clip files บน disk และ DB row
  - `POST /events/purge` — bulk delete ตาม filter (before_dt, camera_id, statuses) พร้อม `dry_run` mode

**Frontend:**
- `frontend/src/api/client.ts` — เพิ่ม `eventsApi.deleteEvent()`, `eventsApi.purge()`
- `frontend/src/views/EventsView.vue`:
  - ปุ่มลบ (ซ่อนถ้าไม่ใช่ ADMIN+) พร้อม confirmation modal แสดง event details
  - Purge modal: slider 0–45 วัน, checkboxes เลือก status, ปุ่ม Preview (dry_run) ก่อนลบจริง
  - Toast notification แจ้งผลหลังลบ

---

### BUG-012 — Bulk purge ลบไม่ได้ — filter ตั้ง default แคบเกินไป

**Severity:** High  
**Component:** Frontend — Events View

**อาการ:**  
กดปุ่ม Bulk Delete แล้ว preview แสดง 0 items แม้จะมี events อยู่จริงหลายรายการ

**สาเหตุ:**  
Default filter: `days=30` + statuses `[ACKNOWLEDGED, SILENCED]` ทำให้ events ใหม่ที่มีสถานะ `NEW` และเกิดขึ้นล่าสุดไม่ตรงเงื่อนไข

**วิธีแก้:**  
เปลี่ยน default เป็น `days=0` (ทุกช่วงเวลา) และ `statuses=[]` (ทุกสถานะ) เพื่อให้ filter รวม events ทุกรายการโดย default

```typescript
// เดิม
const purgeDays = ref(30)
const purgeStatuses = ref(['ACKNOWLEDGED', 'SILENCED'])

// ใหม่
const purgeDays = ref(0)
const purgeStatuses = ref<string[]>([])
```

Backend รองรับ `statuses=[]` = ไม่กรองตาม status (ลบทุกสถานะ)

**ไฟล์ที่แก้:**
- `frontend/src/views/EventsView.vue` — ค่า default ของ purgeDays และ purgeStatuses
- `backend/api/routers/events.py` — ตรวจ `if body.statuses` ก่อน apply filter

---

### BUG-013 — ปุ่มลบ (Delete) หายไปหลัง page refresh

**Severity:** High  
**Component:** Frontend — Auth Store + Router

**อาการ:**  
ปุ่มลบ event แสดงผลถูกต้องหลัง login แต่พอ refresh page ปุ่มหายไปทันที แม้ยังอยู่ในสถานะ ADMIN

**สาเหตุ:**  
`auth.user` เก็บใน Pinia (in-memory) — reset เป็น `null` ทุกครั้งที่ refresh `auth.role` จึง return `''` ทำให้ `canDelete = computed(() => auth.role === 'ADMIN' || ...)` เป็น false

`router.beforeEach` มี guard `if (!auth.user) await auth.fetchMe()` แต่เงื่อนไขเดิมรัน fetchMe **เฉพาะ route ที่มี `meta.roles`** (role-guarded routes) ทำให้ EventsView ที่ require auth แต่ไม่ใช่ role-guarded ไม่ถูก hydrate

**วิธีแก้:**  
เปลี่ยน guard ให้รัน `fetchMe()` สำหรับ **ทุก route ที่ `requiresAuth`** ไม่ใช่แค่ role-guarded

```typescript
// เดิม
if (token && to.meta.roles) {
  if (!auth.user) await auth.fetchMe()
  ...
}

// ใหม่
if (token && to.meta.requiresAuth) {
  if (!auth.user) await auth.fetchMe()   // hydrate ทุก auth route
  const allowedRoles = to.meta.roles as string[] | undefined
  if (allowedRoles && !allowedRoles.includes(auth.role))
    return { name: 'dashboard' }
}
```

**ไฟล์ที่แก้:**
- `frontend/src/router/index.ts` — `router.beforeEach` hydration guard

---

### BUG-014 — Toast notifications ไม่แสดง (`success()`, `error()` silent)

**Severity:** High  
**Component:** Frontend — Toast Store

**อาการ:**  
เรียก `toast.success(...)` หรือ `toast.error(...)` แล้วไม่มี toast แสดงบนหน้าจอเลย ทั้งๆ ที่ไม่มี error ใน console

**สาเหตุ:**  
`toast.ts` store เปิดเผยเฉพาะ `push()` method เดิม แต่ component หลายแห่ง (EventsView, UsersView) เรียก `toast.success()`, `toast.error()`, `toast.warning()`, `toast.info()` ซึ่งไม่เคย implement ไว้

**วิธีแก้:**  
เพิ่ม convenience methods ใน `toast.ts`:

```typescript
function success(title: string, message?: string) {
  push({ type: 'success', title, message: message ?? '' })
}
function error(title: string, message?: string) {
  push({ type: 'error', title, message: message ?? '' })
}
function warning(title: string, message?: string) { ... }
function info(title: string, message?: string) { ... }

return { toasts, push, remove, success, error, warning, info }
```

**ไฟล์ที่แก้:**
- `frontend/src/stores/toast.ts` — เพิ่ม `success()`, `error()`, `warning()`, `info()`

---

### BUG-015 — AuditMiddleware บันทึก actor เป็น "anonymous" เสมอ

**Severity:** Medium  
**Component:** Backend — Audit Middleware + Auth Deps

**อาการ:**  
ทุก audit log entry มี `actor = "anonymous"` แม้จะ login อยู่

**สาเหตุ:**  
`AuditMiddleware.dispatch()` อ่าน `request.state.user` แต่ `get_current_user()` dependency ไม่เคย set ค่านี้ไว้ — `request.state.user` จึงเป็น `None` เสมอ

**วิธีแก้:**  
เพิ่ม `request.state.user = user` ใน `get_current_user()` ก่อน return

```python
# deps.py
request.state.user = user   # ← expose ให้ AuditMiddleware อ่านได้
return user
```

ปรับปรุง `AuditMiddleware` ให้ parse sub-action จาก URL path เพื่อให้ action name descriptive ขึ้น:
```python
# /api/v1/cameras/5/enable  →  action = "cameras.enable"
# /api/v1/cameras  (POST)   →  action = "cameras.post"
if resource and sub_action:
    action = f"{resource}.{sub_action}"
elif resource:
    action = f"{resource}.{request.method.lower()}"
```

**ไฟล์ที่แก้:**
- `backend/api/deps.py` — เพิ่ม `request.state.user = user`
- `backend/api/middleware/audit.py` — parse sub-action จาก URL

---

### FEAT-005 — Audit Trail สำหรับ Camera Enable/Disable

**Component:** Backend + Frontend — Cameras

**เพิ่ม:**

**Backend:**
- `backend/api/routers/cameras.py`:
  - `POST /cameras/{id}/enable` — เปิดกล้อง + บันทึก AuditLog
  - `POST /cameras/{id}/disable` — ปิดกล้อง + บันทึก AuditLog
  - Helper `_set_active()` — เขียน explicit `AuditLog` entry (`action=camera.enable/disable`) พร้อม JSON detail (`previous_is_active`, `new_is_active`, `camera_name`, `source_type`)

**Frontend:**
- `frontend/src/api/client.ts` — เพิ่ม `camerasApi.enable(id)`, `camerasApi.disable(id)`
- `frontend/src/stores/cameras.ts` — `setActive()` เรียก endpoint ใหม่แทน generic PATCH

---

### FEAT-006 — Cascade Enable/Disable: Camera → Zone → Rule

**Component:** Backend + Frontend — Cameras / Zones / Rules

**เพิ่ม:**

เมื่อ enable/disable node หนึ่ง ระบบจะ cascade `is_active` ลงไปยัง children ทุกตัวใน **single DB transaction**:

```
Camera.enable/disable
  └─ Zone.is_active = same  (ทุก zone ของ camera นั้น)
       └─ Rule.is_active = same  (ทุก rule ของ zone นั้น)

Zone.enable/disable
  └─ Rule.is_active = same  (ทุก rule ของ zone นั้น)

Rule.enable/disable  (leaf — ไม่มี cascade)
```

หลัง commit ทุก entity ที่เปลี่ยน: `config_svc.invalidate()` + `config_svc.notify()` เพื่อให้ `RuleEngine` รับ `CONFIG_CHANGED` ทันที ไม่ต้อง restart

**Backend:**
- `cameras.py` — `_set_active()` load zones+rules, bulk update, notify per entity, AuditLog บันทึก `cascaded_zones` + `cascaded_rules`
- `zones.py` — เพิ่ม `POST /zones/{id}/enable|disable` + `_zone_set_active()` cascade rules
- `rules.py` — เพิ่ม `POST /rules/{id}/enable|disable` (leaf)

**Frontend:**
- `client.ts` — เพิ่ม `zonesApi.enable/disable`, `rulesApi.enable/disable`
- `stores/zones.ts` — `patchZone()` delegate ไปยัง `setZoneActive()` เมื่อ field เดียวคือ `is_active`; cascade อัพเดต local rules array
- `ZonesView.vue` — `toggleZone()` เรียก enable/disable endpoint + mirror cascade ใน local rules; `toggleRule()` เรียก dedicated endpoint

**ไฟล์ที่แก้:**
- `backend/api/routers/cameras.py`
- `backend/api/routers/zones.py` (NEW endpoints)
- `backend/api/routers/rules.py` (NEW endpoints)
- `frontend/src/api/client.ts`
- `frontend/src/stores/zones.ts`
- `frontend/src/views/ZonesView.vue`

---

### BUG-016 — Logout ไม่ blacklist refresh token (partial logout)

**Severity:** High  
**Component:** Backend — Auth Router

**อาการ:**  
หลัง logout access token ถูก revoke แต่ refresh token (อายุ 7 วัน) ยังใช้ได้อยู่ ผู้ที่ได้ refresh token ไปสามารถขอ access token ใหม่ได้ต่อเนื่องแม้ user จะ logout แล้ว

**สาเหตุ:**  
`POST /auth/logout` blacklist เฉพาะ access token jti เท่านั้น ไม่ได้รับ refresh_token จาก client และไม่ได้ blacklist มัน

**วิธีแก้:**  
- Backend: `logout` endpoint รับ `refresh_token` optional ใน request body ถ้ามีให้ decode + blacklist jti ของมันด้วย
- Frontend: `auth.ts` ส่ง `localStorage.getItem('refresh_token')` ใน body ของ logout request

```python
# auth.py — logout ใหม่
class LogoutRequest(BaseModel):
    refresh_token: str | None = None

@router.post("/logout")
async def logout(body: LogoutRequest, user: CurrentUser, ...):
    # blacklist access token (from Authorization header)
    ...
    # blacklist refresh token (from body)
    if body.refresh_token:
        rp = decode_token(body.refresh_token, ...)
        if rp.get("type") == "refresh":
            await blacklist_token(rp["jti"], rexp, db)
```

**ไฟล์ที่แก้:**
- `backend/api/routers/auth.py` — `LogoutRequest`, `logout()` endpoint
- `frontend/src/stores/auth.ts` — ส่ง refresh_token ใน logout call
- `frontend/src/api/client.ts` — `authApi.logout(refresh_token?)`

---

### FEAT-007 — Admin กำหนด Token Expiry ได้ผ่าน UI

**Component:** Backend + Frontend — System Settings

**เพิ่ม:**

ผู้ดูแลระบบ (ADMIN/SUPERADMIN) สามารถกำหนดอายุ token ได้ผ่าน Settings → ระบบ โดยไม่ต้อง restart server

**ค่าที่กำหนดได้:**
| Setting | ช่วงที่ยอมรับ | Default |
|---|---|---|
| Access token expiry | 5 นาที – 8 ชั่วโมง | 60 นาที |
| Refresh token expiry | 1 – 90 วัน | 7 วัน |

การเปลี่ยนแปลงมีผลกับ **token ที่ออกใหม่เท่านั้น** (login/refresh ครั้งถัดไป) — token ที่มีอยู่แล้วไม่ได้รับผลกระทบ

**Backend:**
- `models/system_setting.py` (NEW) — key-value table สำหรับ runtime settings (`key`, `value`, `updated_by`, `updated_at`)
- `auth/permissions.py` — เพิ่ม `"system:read"` และ `"system:write"` สำหรับ ADMIN+
- `api/routers/system.py` (NEW) — `GET /system/settings`, `PATCH /system/settings` พร้อม validation (type + range)
- `api/routers/auth.py` — `login()` และ `refresh()` เรียก `_get_setting_int()` เพื่ออ่านค่าจาก DB ก่อน fallback ไป `.env`
- `api/app.py` — register system router

**Frontend:**
- `api/client.ts` — เพิ่ม `SystemSetting` interface + `systemApi.getSettings()`, `systemApi.updateSetting()`
- `views/SettingsView.vue` — Card "การตั้งค่า Token" ใน tab ระบบ (ซ่อนถ้าไม่ใช่ ADMIN+) พร้อม dropdown + save button

---

### FEAT-009 — Evidence Quality Upgrade (Snapshot & Clip)

**Component:** Backend + Frontend — Ingestion / Alert Pipeline / System Settings

**อาการเดิม:**  
ภาพ snapshot และ video clip หลักฐานไม่ชัด เนื่องจาก `CameraThread` encode ทุก frame เป็น THUMBNAIL (320×180, JPEG q60) ก่อนเก็บลง buffer รวมถึง buffer ที่ใช้สำหรับ snapshot และ clip

**สาเหตุ:**  
Architecture เดิมใช้ buffer เดียวกัน (`frame_buffer`) ทั้งสำหรับ AI pipeline, streaming, และ evidence — โดย encode เป็น THUMBNAIL tier เพื่อลด bandwidth และการใช้ RAM เสมอ

**วิธีแก้:**  
แยก buffer 3 ชุดตาม purpose:
- `frame_buffer` (THUMBNAIL 320×180 q60) — AI pipeline + streaming แบบเดิม
- `hires_buffer` (DETAIL 1280×720 q85 default) — snapshot หลักฐาน  
- `clip_buffer` (DETAIL 1280×720 q85 default) — video clip หลักฐาน

**ค่าที่ Admin กำหนดได้ (Settings → ระบบ → คุณภาพหลักฐาน):**
| Setting | ค่าที่ยอมรับ | Default |
|---|---|---|
| Evidence Tier | MONITOR (640×360) / DETAIL (1280×720) / EVIDENCE (ต้นฉบับ) | DETAIL |
| Video CRF | 18–28 (ยิ่งต่ำยิ่งคมชัด) | 23 |

หมายเหตุ: Evidence Tier มีผลหลัง restart server / Video CRF มีผลทันที

**Backend:**
- `ingestion/camera_thread.py` — encode 2 ชุดต่อ frame: THUMBNAIL → `frame_buffer`, evidence_tier → `hires_buffer` + `clip_buffer`
- `ingestion/camera_manager.py` — รับ `hires_buffer` + `evidence_tier`, ส่งต่อ CameraThread, clean up เมื่อ stop
- `alerts/alert_manager.py` — snapshot ดึงจาก `hires_buffer`; `clip_crf` อ่านจาก system_settings DB ทุกครั้ง
- `ingestion/clip_buffer.py` — `save_clip()` + `_apply_faststart()` รับ `crf` param
- `api/routers/system.py` — เพิ่ม `evidence_tier` (enum) + `clip_crf` (int 18–28) settings; `SystemSettingRead` เพิ่ม `type_hint`, `options`, `min`, `max` fields
- `api/app.py` — สร้าง `hires_buffer`, อ่าน quality settings จาก DB ตอน startup, wire ทุก service

**Frontend:**
- `api/client.ts` — อัพเดต `SystemSetting` interface ให้รองรับ `type_hint`, `options`, `min`, `max`
- `views/SettingsView.vue` — เพิ่ม card "คุณภาพหลักฐาน" (ADMIN+) พร้อม dropdown Evidence Tier + CRF

**ไฟล์ที่แก้:**
- `backend/ingestion/camera_thread.py`
- `backend/ingestion/camera_manager.py`
- `backend/alerts/alert_manager.py`
- `backend/ingestion/clip_buffer.py`
- `backend/api/routers/system.py`
- `backend/api/app.py`
- `frontend/src/api/client.ts`
- `frontend/src/views/SettingsView.vue`

---

### FEAT-008 — Signout Confirm Dialog

**Component:** Frontend — AppLayout

**เพิ่ม:**  
ปุ่ม Logout ใน user menu เปิด DaisyUI modal ยืนยันก่อนออกจากระบบแทนที่จะ logout ทันที modal แสดง username ของ session ปัจจุบัน พร้อมปุ่ม "ออกจากระบบ" (error) และ "ยกเลิก"

**ไฟล์ที่แก้:**
- `frontend/src/components/AppLayout.vue` — เพิ่ม `<dialog>` modal + `logoutModal` ref + `handleLogout()` เปลี่ยนเป็นแค่ `showModal()` + `confirmLogout()` รัน logout จริง

---

## 2026-05-18

---

### BUG-017 — Pilot's Console วิดีโอ stream ไม่ชัด และ Admin ไม่สามารถตั้งค่าได้

**Severity:** Medium  
**Component:** Backend — MJPEG Stream / Ingestion

**อาการ:**  
หน้า Pilot's Console แสดงภาพ live stream ไม่ชัด (pixelated)

**สาเหตุ:**  
MJPEG stream endpoint (`GET /cameras/{id}/stream`) อ่านจาก `frame_buffer` ซึ่งเก็บ frame ที่ encode เป็น THUMBNAIL tier (320×180, JPEG q60) เท่านั้น เพราะ `frame_buffer` ออกแบบมาเพื่อ AI pipeline ที่ต้องการ frame เล็ก/เร็ว

**วิธีแก้:**  
เพิ่ม `stream_buffer` (FrameBuffer แยก) ที่ encode frame ที่ `stream_tier` (default MONITOR 640×360 q75) โดย `CameraThread` encode 3 ชุดต่อ frame (thumbnail + evidence + stream) ถ้า stream_tier ต่างกับ evidence_tier; MJPEG endpoint อ่านจาก `stream_buffer` แทน

**ค่าที่ Admin กำหนดได้ (Settings → ระบบ):**
| Setting | ค่าที่ยอมรับ | Default |
|---|---|---|
| Stream Tier | THUMBNAIL (320×180) / MONITOR (640×360) / DETAIL (1280×720) | MONITOR |

มีผลหลัง restart server

**ไฟล์ที่แก้:**
- `backend/ingestion/camera_thread.py` — encode stream_tier → `stream_buffer`
- `backend/ingestion/camera_manager.py` — pass `stream_buffer` + `stream_tier`
- `backend/api/routers/cameras.py` — MJPEG stream อ่านจาก `stream_buffer`
- `backend/api/routers/system.py` — เพิ่ม `stream_tier` setting
- `backend/api/app.py` — สร้าง `stream_buffer`, อ่าน `stream_tier` จาก DB
- `frontend/src/views/SettingsView.vue` — เพิ่ม Stream Tier ใน quality card

---

### BUG-018 — เวลา Events & Alerts แสดงผิด (ช้าไป 7 ชั่วโมง)

**Severity:** High  
**Component:** Backend — Schema Serialization + Frontend — Date Parsing

**อาการ:**  
เวลาใน Events list, Pilot's Console, Dashboard แสดงไม่ตรงกับเวลาจริง — event ที่เกิดตอน 17:30 น. (Bangkok) แสดงเป็น 10:30 น.

**สาเหตุ:**  
SQLite เก็บ datetime เป็น string แบบไม่มี timezone เมื่อ SQLAlchemy อ่านคืนจะได้ naive datetime (no `tzinfo`) Pydantic v2 serialize เป็น `"2026-05-18T10:30:00"` (ไม่มี `Z`) — browser ตีความ string ที่ไม่มี timezone suffix เป็น **local time** ตาม ECMAScript spec แต่ค่าจริงเป็น UTC → แสดงเวลาเร็วไป 7 ชั่วโมง (UTC+7)

**วิธีแก้:**  
สองชั้น:

1. **Backend (root fix):** เพิ่ม `@field_validator` ใน `EventRead` schema ที่ attach `timezone.utc` ให้ naive datetime ก่อนที่ Pydantic จะ serialize → output เป็น `"2026-05-18T10:30:00+00:00"` ซึ่ง browser parse เป็น UTC ถูกต้อง

2. **Frontend (defensive fix):** เพิ่ม helper `parseUtcIso()` ที่ normalize datetime string โดย append `Z` ถ้าไม่มี timezone suffix ใช้แทน `new Date(iso)` ในทุกที่ที่ parse `occurred_at` (EventsView, DashboardView, PilotView, CamerasView)

```python
# schemas/event.py
@field_validator('occurred_at', 'acknowledged_at', mode='before')
@classmethod
def _attach_utc(cls, v):
    if isinstance(v, datetime) and v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v
```

```typescript
// utils/time.ts
export function parseUtcIso(iso: string): Date {
  if (!iso) return new Date(NaN)
  // append Z if no timezone indicator — backend naive datetime = UTC
  const normalized = /[Z+\-]\d*$/.test(iso) ? iso : iso + 'Z'
  return new Date(normalized)
}
```

**ไฟล์ที่แก้:**
- `backend/schemas/event.py` — `@field_validator` attach UTC timezone
- `frontend/src/utils/time.ts` (NEW) — `parseUtcIso()` helper
- `frontend/src/views/EventsView.vue` — ใช้ `parseUtcIso()` ใน `relTime()` + `fmtTime()`
- `frontend/src/views/DashboardView.vue` — ใช้ `parseUtcIso()` ใน `relTime()`
- `frontend/src/views/PilotView.vue` — ใช้ `parseUtcIso()` ใน `fmtTime()` + `hasRecentAlert()`
- `frontend/src/views/CamerasView.vue` — ใช้ `parseUtcIso()` ใน `fmtTime()` + age check

---

### FEAT-010 — Live-reload Stream Tier + Evidence Tier (ไม่ต้อง restart server)

**Component:** Backend — System Settings / CameraManager

**ปัญหาเดิม:**  
`stream_tier` และ `evidence_tier` ถูกอ่านจาก DB ครั้งเดียวตอน server startup และเก็บค้างใน `CameraManager._stream_tier` / `_evidence_tier` — เปลี่ยนค่าใน Settings UI แล้วไม่มีผลจนกว่าจะ restart server

**สาเหตุ:**  
`CameraManager` รับ tier เป็น constructor argument และไม่มีกลไก re-read ค่าเลย

**วิธีแก้:**  
ใช้ `MessageBus CONFIG_CHANGED` pattern ที่มีอยู่แล้วในระบบ (เหมือน camera enable/disable)

```
Admin เปลี่ยน stream_tier ใน UI
  → PATCH /system/settings
  → system.py บันทึก DB + publish CONFIG_CHANGED(scope="system_setting", key, value)
  → CameraManager._on_config_changed() รับ message
  → อัปเดต self._stream_tier / self._evidence_tier
  → _restart_all_cameras() — stop + start ทุก thread (~2-3 วินาที)
  → camera threads ใหม่ encode ที่ tier ใหม่ ✓
```

`clip_crf` ยังคงมีผลทันทีโดยไม่ต้อง restart thread (อ่าน DB ต่อ alert เหมือนเดิม)

**ไฟล์ที่แก้:**
- `backend/api/routers/system.py` — เพิ่ม `Request` param + publish `CONFIG_CHANGED` สำหรับ `stream_tier`/`evidence_tier`
- `backend/ingestion/camera_manager.py` — เพิ่ม `_restart_all_cameras()` + handle `scope="system_setting"` ใน `_on_config_changed()`
- `frontend/src/views/SettingsView.vue` — เปลี่ยน warning note จาก "ต้อง restart" เป็น "restart กล้องสั้นๆ ~2-3 วินาที"

---

## หมายเหตุสถาปัตยกรรม

### Basic Mode vs Advanced Logic Mode

พฤติกรรมของระบบแยกชัดเจนตาม mode ที่ save:

| field | Basic Mode | Advanced Logic Mode |
|---|---|---|
| `rule.logic` | `null` | JSON logic tree |
| `rule.behavior` | ชื่อ behavior | derive จาก tree node แรก |
| `rule.behavior_params` | JSON object | `null` |
| `rule.dwell_threshold_seconds` | ค่าจาก form | อ่านจาก behavior node ใน tree |

Backend ใช้ path แยกกัน: `logic=null` → `_evaluate_legacy()` → อ่าน `behavior_params` top-level; `logic≠null` → recursive tree evaluation → อ่าน params จากแต่ละ node

### Position-Based Dwell (Abandoned Object)

เหตุผลที่ `abandoned_object` ต้องการ position-based key แต่ `loitering` ไม่ต้องการ:
- **Loitering** ตรวจ _คน_ — คนเดินได้ track_id มักเสถียรกว่าเพราะ confidence สูงต่อเนื่อง
- **Abandoned Object** ตรวจ _วัตถุนิ่ง_ — วัตถุนิ่งทำให้ confidence กระพริบบ่อยกว่ามาก เพราะ AI model ถูก train มาให้ detect _motion_ เป็นหลัก
