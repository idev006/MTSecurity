# 12 — Sequence Diagrams
### 3 Key Flows: Detection→Alert · Config Change · Authentication

---

## Flow 1: Camera Frame → LINE Alert (Happy Path)

ลำดับเหตุการณ์หลักของระบบ — ตั้งแต่กล้องจับภาพจนถึง LINE Notify

```
CameraThread  MotionDetector  FrameBuffer  AIPipeline  ObjectTracker  RuleEngine  AlertManager  LineAPI
     │               │              │            │             │             │             │          │
     │─ capture() ──►│              │            │             │             │             │          │
     │               │              │            │             │             │             │          │
     │◄── no motion ─┤  (skip AI)   │            │             │             │             │          │
     │               │              │            │             │             │             │          │
     │─ capture() ──►│              │            │             │             │             │          │
     │               │─ motion! ───►│            │             │             │             │          │
     │               │    put(frame)│            │             │             │             │          │
     │               │              │◄─ get() ───│            │             │             │          │
     │               │              │            │             │             │             │          │
     │               │              │            │─ infer() ──►│            │             │          │
     │               │              │            │  (YOLOv11n) │             │             │          │
     │               │              │            │◄─ detections┤             │             │          │
     │               │              │            │             │             │             │          │
     │               │              │            │─ update() ──────────────►│             │          │
     │               │              │            │             │  ByteTrack  │             │          │
     │               │              │            │◄─ tracks[] ─────────────┤│             │          │
     │               │              │            │             │             │             │          │
     │               │              │   MTP: TRACK_UPDATE published to Bus  │             │          │
     │               │              │            │─────────────────────────►│             │          │
     │               │              │            │             │             │             │          │
     │               │              │            │             │  evaluate() │             │          │
     │               │              │            │             │  (intrusion │             │          │
     │               │              │            │             │   check)    │             │          │
     │               │              │            │             │             │             │          │
     │               │              │   MTP: RULE_TRIGGERED published to Bus│             │          │
     │               │              │            │             │─────────────────────────►│          │
     │               │              │            │             │             │             │          │
     │               │              │            │             │      is_cooldown? NO      │          │
     │               │              │            │             │             │  annotate() │          │
     │               │              │            │             │             │  save snap  │          │
     │               │              │            │             │             │  write DB   │          │
     │               │              │            │             │             │             │          │
     │               │              │            │             │             │─ POST ──────────────►│
     │               │              │            │             │             │             │  LINE    │
     │               │              │            │             │             │◄─ 200 OK ───────────┤│
     │               │              │            │             │             │             │          │
     │               │              │  MTP: ALERT_FIRED published to Bus    │             │          │
     │               │              │            │             │   WebSocket Hub gets msg  │          │
     │               │              │            │             │   → push to Console       │          │
```

### Timing Targets

```
capture() → motion detected       :  < 50 ms   (OpenCV MOG2 เบามาก)
motion detected → TRACK_UPDATE   :  < 200 ms  (OpenVINO inference)
TRACK_UPDATE → RULE_TRIGGERED    :  < 10 ms   (in-memory rule eval)
RULE_TRIGGERED → LINE sent       :  < 2000 ms (network dependent)
RULE_TRIGGERED → Console alert   :  < 100 ms  (WebSocket push)

Total: camera → LINE             :  < 2.5 วินาที  ✅ acceptable
Total: camera → Console          :  < 400 ms       ✅ real-time feel
```

---

## Flow 2: Admin เปลี่ยน Zone Rule → ระบบอัปเดต Real-time

ไม่ต้อง restart — config เปลี่ยนทันทีขณะระบบทำงาน

```
AdminBrowser     API Core     ConfigService    MessageBus   RuleEngine   AlertManager
     │               │              │               │             │             │
     │─ PUT /zones/1 ──────────────►│               │             │             │
     │  {threshold:180}│            │               │             │             │
     │               │              │               │             │             │
     │               │─ update_zone(1, {threshold:180}, "admin_1")             │
     │               │─────────────►│               │             │             │
     │               │              │               │             │             │
     │               │              │─ DB UPDATE zones SET threshold=180─────► │
     │               │              │  WHERE id=1   │             │             │
     │               │              │               │             │             │
     │               │              │─ cache["zones"][1] = updated_zone         │
     │               │              │               │             │             │
     │               │              │─ publish(CONFIG_CHANGED{scope=zone,id=1})─►
     │               │              │               │             │             │
     │               │◄── zone obj ─┤               │             │             │
     │◄── 200 OK ────┤              │               │◄── on_config_changed() ──►│
     │               │              │               │             │             │
     │               │              │               │  RuleEngine reads new     │
     │               │              │               │  threshold from cache     │
     │               │              │               │  (no restart needed)      │
     │               │              │               │             │             │
     │               │              │               │◄────────── AlertManager ──┤
     │               │              │               │  resets cooldown if       │
     │               │              │               │  cooldown_sec changed     │
     │               │              │               │             │             │

AuditLog ถูกบันทึกอัตโนมัติโดย AuditMiddleware:
  actor_id="admin_1", action="PUT /api/v1/zones/1",
  changes={threshold: {old:120, new:180}}, result="success"
```

### ผลลัพธ์ที่ต้องการ

```
PUT /zones/1 request → rule ใหม่มีผล   :  < 100 ms
ไม่มี downtime                          :  ✅
ทุก component ได้ config เดียวกัน      :  ✅ (SSOT pattern)
Audit trail ครบ                         :  ✅
```

---

## Flow 3: User Login → JWT Token → Authenticated Request

```
Browser        API /auth/login    PasswordService   JWTHandler    AuditLog
   │                 │                  │               │             │
   │─ POST /login ──►│                  │               │             │
   │  {user, pass}   │                  │               │             │
   │                 │─ get_user(username) ─────────────────────────► │
   │                 │◄── User{hashed_pw}────────────────────────────┤│
   │                 │                  │               │             │
   │                 │─ verify(plain, hashed) ─────────►│             │
   │                 │◄── True ─────────────────────────┤             │
   │                 │                  │               │             │
   │                 │─ create_access_token(payload) ──►│             │
   │                 │◄── "eyJhbGci..." ────────────────┤             │
   │                 │─ create_refresh_token(user_id) ─►│             │
   │                 │◄── "eyJhbGci..." ────────────────┤             │
   │                 │                  │               │             │
   │                 │─ write audit(login.success) ─────────────────►│
   │◄── 200 {access_token, refresh_token, actor} ────────────────────┤
   │                 │                  │               │             │
   │                 │                  │               │             │
   │  [เก็บ token ใน Pinia store]        │               │             │
   │                 │                  │               │             │
   │─ GET /events/ ──────────────────────────────────────────────────►
   │  Authorization: Bearer eyJhbGci...│               │             │
   │                 │                  │               │             │
   │                 │─ decode_token() ─────────────────────────────► │
   │                 │◄── payload{sub, actor_type, scopes, camera_ids}│
   │                 │                  │               │             │
   │                 │─ is_revoked(jti)?─────────────────────────────►│
   │                 │◄── False (not in blacklist) ─────────────────  │
   │                 │                  │               │             │
   │                 │─ check_permission(actor_type, "events:read") ──►
   │                 │◄── allowed        │               │             │
   │                 │                  │               │             │
   │◄── 200 {events}─┤                  │               │             │
```

### Login Failure Flow

```
Browser        API /auth/login    PasswordService
   │                 │                  │
   │─ POST /login ──►│                  │
   │  {wrong pass}   │                  │
   │                 │─ verify(plain, hashed) ─────────►
   │                 │◄── False ──────────────────────
   │                 │                  │
   │                 │─ write audit(login.failed, ip=x.x.x.x) ──────►
   │                 │─ check rate_limit (5/min per IP) ─────────────►
   │◄── 401 NOT_AUTHENTICATED ───────────────────────────────────────
```

---

## Flow 4: Camera Reconnect (Failure Recovery)

```
CameraThread    StateRegistry    MessageBus    CameraManager
     │                │               │              │
     │─ read frame ──►│               │              │
     │◄── RTSP error ─┤               │              │
     │                │               │              │
     │─ set_status(cam_id, "error") ──►              │
     │                │               │              │
     │─ publish(CAMERA_DISCONNECTED) ─────────────►  │
     │                │               │   API WebSocket Hub gets msg
     │                │               │   → Console thumbnail border = ⚫
     │                │               │              │
     │─ wait 5s ──────────────────────────────────── │
     │─ VideoCapture(rtsp_url) ───────────────────── │
     │                │               │              │
     │  [success]     │               │              │
     │─ set_status(cam_id, "online") ─►              │
     │─ publish(CAMERA_CONNECTED) ────────────────►  │
     │                │               │   Console thumbnail border = 🟢
     │                │               │              │
     │  [fail again]  │               │              │
     │─ reconnect_count += 1 ─────────►              │
     │─ wait exponential backoff (5s → 10s → 20s) ── │
     │─ publish(HEALTH_BEAT{status="degraded"}) ───► │
```

---

## Flow 5: Operator Acknowledges Alert

```
OperatorBrowser   API /alerts/ack   DB(events)   MessageBus   WebSocket Hub
      │                 │               │              │              │
      │─ POST /events/1001/acknowledge ─►              │              │
      │  {note: "ตรวจสอบแล้ว"}         │              │              │
      │                 │               │              │              │
      │                 │─ check permission(operator, "alerts:acknowledge")
      │                 │─ check camera_ids scope (cam 3 ∈ operator scope?)
      │                 │               │              │              │
      │                 │─ UPDATE events SET is_acknowledged=true ──► │
      │                 │─ INSERT alert_notes(event_id, note) ──────► │
      │                 │               │              │              │
      │                 │─ publish(ALERT_ACK{event_id=1001}) ────────►│
      │                 │               │  all connected consoles get msg
      │                 │               │  → alert removed from queue  │
      │                 │               │              │              │
      │◄── 200 {is_acknowledged: true} ─┤              │              │
      │                 │               │              │              │
      │                 │─ write audit(alert.acknowledge, event/1001)─►
```
