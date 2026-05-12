# 05 — Pilot's Console
### Master Control Center · Situational Awareness · Immediate Action

---

## 1. แนวคิด: ห้องนักบิน ไม่ใช่ Dashboard

Dashboard ทั่วไป: แสดงข้อมูล → ผู้ใช้ interpret → ผู้ใช้ตัดสินใจ → ผู้ใช้หา control → ผู้ใช้ action
Pilot's Console: แสดงข้อมูล + interpret + **action ทำได้ทันที ณ จุดที่เห็น**

นักบินใน cockpit ไม่ต้องค้นหาปุ่ม — ทุกอย่างอยู่ในสายตา พร้อมใช้งาน
เจ้าหน้าที่รักษาความปลอดภัยก็ต้องได้รับ UX แบบเดียวกัน

**หลักการ 3 ข้อ:**
```
1. AWARENESS : เห็นทุกอย่างที่สำคัญในหน้าจอเดียว ไม่ต้อง navigate
2. PRIORITY  : สิ่งที่สำคัญที่สุดต้องเด่นที่สุด — alert ≠ statistics
3. ACTION    : จาก "เห็น" ถึง "ทำ" ไม่เกิน 2 คลิก
```

---

## 2. Layout Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ [🔴 LIVE]  MTSecurity Pilot's Console          [Operator: สมชาย] [22:14:05] │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────────────────────────┐  ┌──────────────────────────────────┐  │
│  │                                 │  │  🚨 ALERT QUEUE               (3) │  │
│  │     PRIMARY CAMERA FEED         │  │ ─────────────────────────────── │  │
│  │     [CAM-03 ประตูหลัง]          │  │ 🔴 22:14:02 INTRUSION           │  │
│  │     [Bounding boxes + Zones]    │  │    CAM-03 | person | Zone-A     │  │
│  │     [Track IDs visible]         │  │    [VIEW] [ACK] [ESCALATE]      │  │
│  │                                 │  │ ─────────────────────────────── │  │
│  │                                 │  │ 🟡 22:13:45 LOITERING           │  │
│  └─────────────────────────────────┘  │    CAM-01 | person | ATM Zone   │  │
│                                        │    [VIEW] [ACK] [SILENCE 15m]  │  │
│  ┌──────────────────────────────────┐  │ ─────────────────────────────── │  │
│  │  CAMERA GRID (Thumbnail x9)      │  │ 🟡 22:12:00 ABANDONED OBJECT   │  │
│  │  [1][2][●3][4][5]               │  │    CAM-07 | bag | Entry Zone    │  │
│  │  [6][7][8][9][+]               │  │    [VIEW] [ACK]                 │  │
│  │  ● = active alert camera        │  └──────────────────────────────────┘  │
│  └──────────────────────────────────┘                                        │
│                                        ┌──────────────────────────────────┐  │
│  ┌──────────────────────────────────┐  │  SYSTEM HEALTH                   │  │
│  │  RECENT EVENTS                   │  │ ─────────────────────────────── │  │
│  │  22:14:02 INTRUSION CAM-03 🔴   │  │ AI Engine    [████████░░] 80%   │  │
│  │  22:13:45 LOITERING CAM-01 🟡   │  │ Cameras      9/10 Online  🟢   │  │
│  │  22:12:00 ABANDONED CAM-07 🟡   │  │ DB           OK           🟢   │  │
│  │  22:10:30 LINE CROSSING CAM-02  │  │ Disk         312GB free   🟢   │  │
│  │  22:08:15 INTRUSION CAM-03 🔴   │  │ Last Alert   14 sec ago        │  │
│  └──────────────────────────────────┘  └──────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Component ของ Console

### 3.1 Primary Camera Feed
```
ตำแหน่ง : ซ้ายบน (พื้นที่ใหญ่สุด)
แสดง    : Live feed กล้องที่ active alert หรือกล้องที่ operator เลือก
Overlay :
  - Bounding boxes (สีตาม class: แดง=person, เหลือง=car, เขียว=animal)
  - Zone boundaries (สีตาม rule severity)
  - Track IDs (#42, #43...)
  - Dwell time indicator (ถ้า loitering: แสดง "147s / 180s")
  - Zone name label
```

### 3.2 Camera Grid (Thumbnail)
```
ตำแหน่ง : ซ้ายล่าง
แสดง    : Thumbnail ทุกกล้อง (5 FPS)
State   :
  🟢 border = online, ไม่มี alert
  🔴 border = active alert (กระพริบ)
  ⚫ border = offline
  ● = active alert indicator บน thumbnail

Action  : คลิกที่ thumbnail → Primary Feed เปลี่ยนไปดูกล้องนั้น
```

### 3.3 Alert Queue
```
ตำแหน่ง : ขวาบน
Priority : เรียงจาก severity สูง → ต่ำ, แล้วตาม timestamp ล่าสุด
Per Alert:
  - Severity badge (🔴 HIGH, 🟡 MEDIUM, ⚪ LOW)
  - Timestamp + event type
  - Camera name + zone name
  - Object class

Actions per Alert:
  [VIEW]      → Primary Feed โฟกัสกล้องนั้น + snapshot popup
  [ACK]       → mark acknowledged + ให้ระบุหมายเหตุ
  [SILENCE Nm]→ extend cooldown N นาที (OPERATOR สามารถ override ได้)
  [ESCALATE]  → ส่งต่อไปยัง supervisor (email/LINE)
```

### 3.4 Recent Events Timeline
```
ตำแหน่ง : ซ้ายล่าง (ด้านล่าง camera grid)
แสดง    : Event 20 รายการล่าสุด (real-time append)
Filter  : ปุ่ม toggle: ALL | UNACKNOWLEDGED | HIGH ONLY
```

### 3.5 System Health Panel
```
ตำแหน่ง : ขวาล่าง
แสดง    :
  - AI Engine CPU usage + actual FPS
  - Camera online count
  - DB status
  - Disk free space
  - Redis status
  - Last alert time
  - Uptime

Color coding:
  🟢 = OK (> threshold)
  🟡 = Warning (approaching limit)
  🔴 = Critical (action needed)
```

---

## 4. Alert Detail Popup

เมื่อกด [VIEW] หรือ alert ใหม่เข้ามา:

```
┌─────────────────────────────────────────────────────────┐
│ 🔴 INTRUSION DETECTED                        22:14:02   │
├─────────────────────────────────────────────────────────┤
│  Camera  : CAM-03 ประตูหลัง                             │
│  Zone    : โซนอันตราย-เครื่องจักร                       │
│  Object  : Person (confidence: 87%)                     │
│  Track   : #42  |  Dwell: 3.2s                         │
├───────────────────┬─────────────────────────────────────┤
│  [SNAPSHOT IMAGE] │  Timeline of Track #42:             │
│  640×360 JPEG     │  22:14:00 ─── entered Zone          │
│  with bbox drawn  │  22:14:02 ─── INTRUSION triggered   │
│                   │  22:14:02 ─── LINE sent ✓           │
│                   │  22:14:02 ─── Webhook sent ✓        │
├───────────────────┴─────────────────────────────────────┤
│  Notes: ___________________________________________      │
│                                                          │
│  [ACK + Save Note]  [ESCALATE]  [VIEW CAMERA]  [CLOSE]  │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Keyboard Shortcuts (Power User)

```
Space       → Acknowledge latest unacknowledged alert
1-9, 0      → Switch primary feed to camera 1-10
F           → Toggle fullscreen primary feed
A           → Open alert detail of latest alert
S           → Silence latest alert (15 min)
H           → Toggle system health panel
M           → Mute/Unmute alert sound
Esc         → Close popup / return to grid view
```

---

## 6. WebSocket Events ที่ Console รับ

```typescript
// Console subscribes to /ws/alerts และ /ws/stream/{camera_id}

// Event types that trigger UI update:
interface MTPWebSocketMessage {
  type: "alert" | "frame" | "camera_status" | "health_beat" | "alert_ack"
}

// "alert" → เพิ่มใน Alert Queue, กระพริบ camera thumbnail, เล่น sound
// "frame" → อัปเดต Primary Feed + thumbnail
// "camera_status" → อัปเดต System Health panel, thumbnail border color
// "health_beat"   → อัปเดต System Health panel metrics
// "alert_ack"     → ลบออกจาก Alert Queue (ถ้า operator อื่น ACK ไปแล้ว)
```

---

## 7. Role-based Console View

```
SUPERADMIN / ADMIN view:
  + เห็นทุกกล้อง
  + เห็น System Health ครบ
  + มีปุ่ม [CONFIGURE ZONE], [EDIT RULE] บน primary feed

OPERATOR view:
  + เห็นเฉพาะกล้องที่ได้รับมอบหมาย
  + System Health แสดงแค่ camera status
  + ไม่มีปุ่ม configure
  + มีปุ่ม ACK, SILENCE, ESCALATE, NOTE

AUDITOR view:
  + Read-only ทั้งหมด
  + ไม่มี ACK / SILENCE / ESCALATE
  + เห็น historical events เท่านั้น (ไม่มี live feed)
```
