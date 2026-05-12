# 09 — API Reference
### REST Endpoints · Request/Response Schemas · Error Codes · WebSocket Events

---

## 1. Conventions

```
Base URL (dev)  : http://localhost:8000
Base URL (prod) : https://yourdomain.com

Authentication  : Bearer JWT token ใน Authorization header
                  Authorization: Bearer <access_token>

Content-Type    : application/json (ทุก request/response)
API Version     : /api/v1/ (prefix ทุก endpoint ยกเว้น /health, /ws)

Timestamp format: ISO 8601 — "2025-05-11T14:30:00Z"
ID type         : integer (auto-increment)
```

---

## 2. Error Schema (มาตรฐานทุก endpoint)

```json
{
  "detail": "Human-readable error message",
  "code":   "ERROR_CODE_CONSTANT",
  "field":  "field_name"    // optional — มีเฉพาะ validation error
}
```

### Error Codes

```
HTTP 400  BAD_REQUEST          — request body / query param ผิด format
HTTP 401  NOT_AUTHENTICATED    — ไม่มี token หรือ token หมดอายุ
HTTP 401  TOKEN_REVOKED        — token ถูก revoke แล้ว
HTTP 403  PERMISSION_DENIED    — actor ไม่มีสิทธิ์ใช้ endpoint นี้
HTTP 403  SCOPE_RESTRICTED     — actor มีสิทธิ์ แต่ไม่ใช่ resource ที่ได้รับมอบหมาย
HTTP 404  NOT_FOUND            — resource ไม่มีอยู่
HTTP 409  ALREADY_EXISTS       — duplicate (เช่น camera RTSP ซ้ำ)
HTTP 422  VALIDATION_ERROR     — Pydantic validation fail
HTTP 429  RATE_LIMIT_EXCEEDED  — เกิน rate limit
HTTP 500  INTERNAL_ERROR       — server error (ดู server log)
HTTP 503  SERVICE_UNAVAILABLE  — dependency (AI, DB) ไม่พร้อม
```

---

## 3. Authentication

### POST /api/v1/auth/login

```
สิทธิ์ : Public (ไม่ต้อง token)
Rate   : 5 req/minute per IP
```

**Request**
```json
{
  "username": "admin_1",
  "password": "P@ssword1234"
}
```

**Response 200**
```json
{
  "access_token":  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type":    "bearer",
  "expires_in":    28800,
  "actor": {
    "id":           1,
    "username":     "admin_1",
    "display_name": "สมชาย วิศวกร",
    "actor_type":   "admin",
    "camera_ids":   []
  }
}
```

**Response 401**
```json
{ "detail": "Invalid username or password", "code": "NOT_AUTHENTICATED" }
```

---

### POST /api/v1/auth/refresh

```
สิทธิ์ : ต้องมี refresh_token (ใส่ใน body)
```

**Request**
```json
{ "refresh_token": "eyJhbGci..." }
```

**Response 200** — เหมือน login response (token ใหม่ทั้งคู่)

---

### POST /api/v1/auth/logout

```
สิทธิ์ : ทุก actor (ต้องมี access_token)
Action : blacklist ทั้ง access_token และ refresh_token
```

**Response 200**
```json
{ "message": "Logged out successfully" }
```

---

## 4. Cameras

### GET /api/v1/cameras/

```
สิทธิ์ : superadmin, admin, operator* (* เฉพาะที่ได้รับมอบหมาย), auditor*
```

**Query Parameters**
```
is_active   bool    optional  — กรองเฉพาะกล้องที่ active
zone        int     optional  — กรองตาม zone_id
```

**Response 200**
```json
[
  {
    "id":          1,
    "name":        "ประตูหน้า",
    "location":    "อาคาร A ชั้น 1",
    "zone_label":  "critical",
    "fps_target":  10,
    "is_active":   true,
    "created_at":  "2025-05-01T08:00:00Z",
    "status": {
      "online":         true,
      "fps_actual":     9.8,
      "last_frame_at":  "2025-05-11T14:30:00Z",
      "reconnect_count": 0
    }
  }
]
```

---

### POST /api/v1/cameras/

```
สิทธิ์ : superadmin, admin
Audit  : ✓ บันทึก audit log
```

**Request**
```json
{
  "name":       "ประตูหน้า",
  "location":   "อาคาร A ชั้น 1",
  "rtsp_url":   "rtsp://admin:pass@192.168.1.101/stream",
  "zone_label": "critical",
  "fps_target": 10,
  "is_active":  true
}
```

**Response 201**
```json
{
  "id":         1,
  "name":       "ประตูหน้า",
  "location":   "อาคาร A ชั้น 1",
  "zone_label": "critical",
  "fps_target": 10,
  "is_active":  true,
  "created_at": "2025-05-11T14:30:00Z"
}
```

---

### POST /api/v1/cameras/{id}/test

```
สิทธิ์  : superadmin, admin
Action  : ทดสอบ RTSP connection — ไม่บันทึกข้อมูลใดๆ
Timeout : 5 วินาที
```

**Response 200**
```json
{
  "reachable":    true,
  "latency_ms":   45,
  "resolution":   "1920x1080",
  "codec":        "H.264"
}
```

**Response 200 (failed)**
```json
{
  "reachable":  false,
  "latency_ms": null,
  "error":      "Connection refused"
}
```

---

### GET /api/v1/cameras/{id}

**Response 200** — เหมือน array item ด้านบน + รายการ zones

---

### PUT /api/v1/cameras/{id}

```
สิทธิ์ : superadmin, admin
Audit  : ✓
Action : update config → SSOT CONFIG_CHANGED broadcast
```

**Request** — ส่งเฉพาะ field ที่ต้องการแก้
```json
{
  "fps_target": 5,
  "is_active":  false
}
```

---

### DELETE /api/v1/cameras/{id}

```
สิทธิ์  : superadmin, admin
Audit   : ✓
Action  : soft delete (is_active = false) — ไม่ลบ events ที่เกิดขึ้นแล้ว
```

---

## 5. Zones

### GET /api/v1/zones/

```
Query: camera_id (int, optional), is_active (bool, optional)
สิทธิ์: superadmin, admin, operator*
```

**Response 200**
```json
[
  {
    "id":        1,
    "camera_id": 1,
    "name":      "โซนอันตราย",
    "zone_type": "polygon",
    "coords":    [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]],
    "color_hex": "#FF0000",
    "is_active": true,
    "rules": [
      {
        "id":         1,
        "rule_type":  "intrusion",
        "is_active":  true
      }
    ]
  }
]
```

---

### POST /api/v1/zones/

```
สิทธิ์ : superadmin, admin
Audit  : ✓
```

**Request**
```json
{
  "camera_id":  1,
  "name":       "โซนอันตราย",
  "zone_type":  "polygon",
  "coords":     [[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]],
  "color_hex":  "#FF0000"
}
```

**zone_type values:**
- `polygon` — พื้นที่ปิด (ต้องการ ≥ 3 จุด)
- `tripwire` — เส้นตัด (ต้องการ 2 จุดเท่านั้น)

---

### PUT /api/v1/zones/{id}

```
Action : update → SSOT CONFIG_CHANGED → RuleEngine, AlertManager อัปเดตทันที
```

---

## 6. Rules

### GET /api/v1/rules/

```
Query: zone_id (int, optional)
สิทธิ์: superadmin, admin
```

**Response 200**
```json
[
  {
    "id":            1,
    "zone_id":       1,
    "rule_type":     "intrusion",
    "target_class":  "person",
    "threshold":     0,
    "cooldown_sec":  30,
    "schedule": {
      "always_on":  false,
      "time_from":  "22:00",
      "time_to":    "06:00",
      "weekdays":   [0, 1, 2, 3, 4, 5, 6]
    },
    "is_active":     true
  }
]
```

**rule_type values:**
```
intrusion         — คนเข้าพื้นที่ห้าม
loitering         — อยู่นานเกิน threshold (วินาที)
line_crossing     — ข้ามเส้น tripwire
crowd_density     — จำนวนคนเกิน threshold
abandoned_object  — วางของทิ้งไว้นานเกิน threshold
```

---

### POST /api/v1/rules/

```
สิทธิ์ : superadmin, admin
Audit  : ✓
```

**Request**
```json
{
  "zone_id":       1,
  "rule_type":     "loitering",
  "target_class":  "person",
  "threshold":     180,
  "cooldown_sec":  60,
  "schedule": {
    "always_on":  true
  }
}
```

---

## 7. Events

### GET /api/v1/events/

```
สิทธิ์: superadmin, admin, operator* (เฉพาะกล้องที่ได้รับมอบหมาย), auditor
```

**Query Parameters**
```
camera_id       int       optional
event_type      string    optional   intrusion | loitering | line_crossing | ...
object_class    string    optional   person | car | bag | ...
date_from       datetime  optional   ISO8601
date_to         datetime  optional   ISO8601
is_alerted      bool      optional
is_acknowledged bool      optional
limit           int       default=50, max=500
offset          int       default=0
```

**Response 200**
```json
{
  "total": 1250,
  "items": [
    {
      "id":              1001,
      "camera_id":       3,
      "camera_name":     "CAM-03 ประตูหลัง",
      "zone_id":         2,
      "zone_name":       "โซนอันตราย",
      "event_type":      "intrusion",
      "track_id":        42,
      "object_class":    "person",
      "confidence":      0.87,
      "bbox":            {"x1": 0.3, "y1": 0.2, "x2": 0.6, "y2": 0.9},
      "dwell_time":      3.2,
      "occurred_at":     "2025-05-11T22:14:02Z",
      "is_alerted":      true,
      "is_acknowledged": false,
      "snapshot_url":    "/api/v1/events/1001/snapshot",
      "mtp_correlation": "abc-123-def-456",
      "notes":           []
    }
  ]
}
```

---

### GET /api/v1/events/{id}/snapshot

```
สิทธิ์       : superadmin, admin, operator*, auditor
Content-Type : image/jpeg
Response     : Binary JPEG image
```

---

### POST /api/v1/events/{id}/acknowledge

```
สิทธิ์  : superadmin, admin, operator
Audit   : ✓
```

**Request**
```json
{
  "note": "ส่ง รปภ. ไปตรวจสอบแล้ว — พบว่าเป็นพนักงานทำงานดึก"
}
```

**Response 200**
```json
{
  "id":              1001,
  "is_acknowledged": true,
  "acknowledged_at": "2025-05-11T22:15:30Z",
  "acknowledged_by": "operator_sompong"
}
```

---

### POST /api/v1/events/{id}/silence

```
สิทธิ์  : superadmin, admin, operator
Action  : ขยาย cooldown ชั่วคราวโดยไม่แก้ Rule config
Audit   : ✓
```

**Request**
```json
{ "minutes": 15 }
```

---

### POST /api/v1/events/{id}/escalate

```
สิทธิ์  : superadmin, admin, operator
Action  : ส่ง notification พิเศษไปยัง supervisor
Audit   : ✓
```

**Request**
```json
{ "note": "สถานการณ์ต้องการการตัดสินใจจากผู้บริหาร" }
```

---

## 8. Analytics

### GET /api/v1/analytics/summary

```
Query  : date_from, date_to, camera_id (optional)
สิทธิ์ : superadmin, admin, auditor
```

**Response 200**
```json
{
  "period": {
    "from": "2025-05-01T00:00:00Z",
    "to":   "2025-05-11T23:59:59Z"
  },
  "totals": {
    "events":          342,
    "alerts_fired":    89,
    "acknowledged":    85,
    "unacknowledged":  4
  },
  "by_event_type": {
    "intrusion":    45,
    "loitering":    28,
    "line_crossing": 16
  },
  "by_camera": [
    { "camera_id": 3, "camera_name": "CAM-03", "event_count": 120 }
  ],
  "avg_response_time_sec": 42.5
}
```

---

### GET /api/v1/analytics/heatmap/{camera_id}

```
Query  : date_from, date_to
สิทธิ์ : superadmin, admin, auditor
```

**Response 200**
```json
{
  "camera_id": 3,
  "resolution": { "width": 64, "height": 36 },
  "grid": [[0, 2, 5, 0, 0], [0, 0, 8, 12, 3]],
  "max_value": 45
}
```

---

### GET /api/v1/analytics/hourly/{camera_id}

```
Query  : date (YYYY-MM-DD)
สิทธิ์ : superadmin, admin, auditor
```

**Response 200**
```json
{
  "camera_id": 3,
  "date": "2025-05-11",
  "hours": [
    { "hour": 0,  "event_count": 2 },
    { "hour": 1,  "event_count": 0 },
    { "hour": 22, "event_count": 15 }
  ]
}
```

---

## 9. System & Health

### GET /api/health

```
สิทธิ์ : Public (ไม่ต้อง token) — ใช้สำหรับ load balancer health check
```

**Response 200**
```json
{ "status": "ok", "timestamp": "2025-05-11T14:30:00Z" }
```

---

### GET /api/v1/system/health

```
สิทธิ์ : superadmin, admin
```

**Response 200**
```json
{
  "overall": "ok",
  "cameras": { "online": 9, "total": 10 },
  "services": {
    "ai.engine": {
      "status":  "ok",
      "metrics": { "fps": 8.5, "cpu_pct": 72.3, "queue_depth": 2 }
    },
    "alert.manager": {
      "status":  "ok",
      "metrics": { "cooldowns_active": 3 }
    }
  },
  "database": { "status": "ok", "size_mb": 142 },
  "disk": { "free_gb": 312.4, "total_gb": 512 },
  "stale_services": [],
  "uptime_sec": 86400
}
```

---

### GET /api/v1/system/audit-log

```
สิทธิ์ : superadmin, auditor
Query  : actor_id, action, date_from, date_to, limit (max 1000), offset
```

**Response 200**
```json
{
  "total": 5420,
  "items": [
    {
      "id":         1001,
      "actor_id":   "admin_1",
      "actor_type": "admin",
      "action":     "zone.update",
      "resource":   "zone/15",
      "changes": {
        "threshold": { "old": 120, "new": 180 }
      },
      "ip_address": "192.168.1.50",
      "result":     "success",
      "timestamp":  "2025-05-11T14:30:00Z"
    }
  ]
}
```

---

## 10. Users (Superadmin Only)

### GET /api/v1/users/

```
สิทธิ์ : superadmin เท่านั้น
```

**Response 200**
```json
[
  {
    "id":           1,
    "username":     "admin_1",
    "display_name": "สมชาย วิศวกร",
    "actor_type":   "admin",
    "camera_ids":   [],
    "is_active":    true,
    "last_login":   "2025-05-11T08:00:00Z"
  }
]
```

---

### POST /api/v1/users/

```
สิทธิ์ : superadmin
Audit  : ✓
```

**Request**
```json
{
  "username":     "operator_guard1",
  "display_name": "สมปอง รักษาการ",
  "password":     "P@ssword1234",
  "actor_type":   "operator",
  "camera_ids":   [1, 3, 5]
}
```

---

## 11. LPR (License Plate Recognition)

### GET /api/v1/lpr/whitelist/

```
สิทธิ์ : superadmin, admin
```

**Response 200**
```json
[
  {
    "id":          1,
    "plate":       "กข-1234",
    "description": "รถผู้บริหาร",
    "is_active":   true,
    "expires_at":  null
  }
]
```

---

### POST /api/v1/lpr/whitelist/

```
สิทธิ์ : superadmin, admin, ext_system* (ถ้า scope = lpr:write)
Audit  : ✓
```

**Request**
```json
{
  "plate":       "กข-1234",
  "description": "รถผู้บริหาร",
  "expires_at":  null
}
```

---

## 12. WebSocket Events

### WS /ws/alerts

```
สิทธิ์ : ต้องส่ง token ใน query param: /ws/alerts?token=<access_token>
```

**Event: alert_fired**
```json
{
  "type":      "alert",
  "event": {
    "id":           1001,
    "event_type":   "intrusion",
    "camera_id":    3,
    "camera_name":  "CAM-03 ประตูหลัง",
    "zone_name":    "โซนอันตราย",
    "object_class": "person",
    "confidence":   0.87,
    "occurred_at":  "2025-05-11T22:14:02Z",
    "snapshot_url": "/api/v1/events/1001/snapshot"
  }
}
```

**Event: alert_acknowledged**
```json
{
  "type":     "alert_ack",
  "event_id": 1001,
  "ack_by":   "operator_sompong",
  "ack_at":   "2025-05-11T22:15:30Z"
}
```

**Event: camera_status**
```json
{
  "type":      "camera_status",
  "camera_id": 3,
  "status":    "offline",
  "timestamp": "2025-05-11T22:14:00Z"
}
```

**Event: health_beat**
```json
{
  "type":    "health_beat",
  "service": "ai.engine",
  "status":  "ok",
  "metrics": { "fps": 8.5, "cpu_pct": 72.3 }
}
```

---

### WS /ws/stream/{camera_id}

```
สิทธิ์  : ต้องมีสิทธิ์ดูกล้อง camera_id นั้น
Protocol: รับ frame เป็น Binary (JPEG bytes)
Rate    : ตาม fps_target ของกล้อง (default 5 FPS สำหรับ thumbnail)
```

---

## 13. Export

### GET /api/v1/export/events

```
สิทธิ์        : superadmin, admin, auditor
Query         : date_from, date_to, camera_id, format (csv|json)
Content-Type  : text/csv หรือ application/json (ตาม format)
```

---

## 14. API Key Management

### POST /api/v1/api-keys/

```
สิทธิ์  : superadmin, admin
Audit   : ✓
หมายเหตุ: plain key ส่งกลับครั้งเดียวเท่านั้น — ไม่สามารถดูได้อีก
```

**Request**
```json
{
  "name":       "ระบบควบคุมประตู",
  "scopes":     ["alerts:read", "events:read"],
  "camera_ids": [1, 2],
  "expires_at": "2026-05-11T00:00:00Z"
}
```

**Response 201**
```json
{
  "id":          1,
  "name":        "ระบบควบคุมประตู",
  "key":         "mts_abc123...",
  "scopes":      ["alerts:read", "events:read"],
  "camera_ids":  [1, 2],
  "expires_at":  "2026-05-11T00:00:00Z",
  "warning":     "Save this key now. It will not be shown again."
}
```

---

## 15. Endpoint Summary Table

```
Method  Path                                  Actor         Rate
──────────────────────────────────────────────────────────────────────
POST    /api/v1/auth/login                   public        5/min
POST    /api/v1/auth/refresh                 token         20/min
POST    /api/v1/auth/logout                  any actor     20/min

GET     /api/v1/cameras/                     adm+opr+aud   100/min
POST    /api/v1/cameras/                     adm           100/min
POST    /api/v1/cameras/{id}/test            adm           20/min
GET     /api/v1/cameras/{id}                 adm+opr+aud   100/min
PUT     /api/v1/cameras/{id}                 adm           100/min
DELETE  /api/v1/cameras/{id}                 adm           20/min

GET     /api/v1/zones/                       adm+opr       100/min
POST    /api/v1/zones/                       adm           100/min
PUT     /api/v1/zones/{id}                   adm           100/min
DELETE  /api/v1/zones/{id}                   adm           20/min

GET     /api/v1/rules/                       adm           100/min
POST    /api/v1/rules/                       adm           100/min
PUT     /api/v1/rules/{id}                   adm           100/min

GET     /api/v1/events/                      adm+opr+aud   100/min
GET     /api/v1/events/{id}/snapshot         adm+opr+aud   30/min
POST    /api/v1/events/{id}/acknowledge      adm+opr       100/min
POST    /api/v1/events/{id}/silence          adm+opr       20/min
POST    /api/v1/events/{id}/escalate         adm+opr       20/min

GET     /api/v1/analytics/summary            adm+aud       30/min
GET     /api/v1/analytics/heatmap/{id}       adm+aud       30/min
GET     /api/v1/analytics/hourly/{id}        adm+aud       30/min

GET     /api/health                          public        unlimited
GET     /api/v1/system/health                adm           30/min
GET     /api/v1/system/audit-log             sadm+aud      30/min

GET     /api/v1/users/                       sadm          100/min
POST    /api/v1/users/                       sadm          20/min
PUT     /api/v1/users/{id}                   sadm          20/min

GET     /api/v1/lpr/whitelist/               adm           100/min
POST    /api/v1/lpr/whitelist/               adm+ext*      100/min

GET     /api/v1/export/events                adm+aud       5/min

POST    /api/v1/api-keys/                    adm           20/min
DELETE  /api/v1/api-keys/{id}                adm           20/min

WS      /ws/alerts                           adm+opr       —
WS      /ws/stream/{camera_id}               adm+opr       —

sadm = superadmin, adm = admin, opr = operator, aud = auditor
ext* = external system (ถ้า scope อนุญาต), * = scoped access
```
