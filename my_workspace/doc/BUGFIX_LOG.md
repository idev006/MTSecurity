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
| `backend/ingestion/clip_buffer.py` | FEAT-003 (NEW) |
| `backend/alerts/alert_manager.py` | FEAT-003 |
| `backend/api/routers/events.py` | FEAT-003 |
| `backend/api/routers/users.py` | FEAT-002 |
| `backend/api/app.py` | FEAT-003 |
| `frontend/src/components/RuleLogicBuilder.vue` | BUG-003, BUG-005 |
| `frontend/src/views/ZonesView.vue` | BUG-003, BUG-006, BUG-007 |
| `frontend/src/views/UsersView.vue` | FEAT-001 (NEW) |
| `frontend/src/views/SettingsView.vue` | FEAT-002 |
| `frontend/src/views/EventsView.vue` | FEAT-003 |
| `frontend/src/api/client.ts` | FEAT-001 |
| `frontend/src/router/index.ts` | FEAT-001 |
| `frontend/src/components/AppLayout.vue` | FEAT-001 |

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
