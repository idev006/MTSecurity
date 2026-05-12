# 04 — Key Flows (Sequence Diagrams)

เอกสารนี้แสดง 5 เส้นทางวิกฤตที่ต้องเข้าใจให้ถ่องแท้ก่อนลงมือเขียนโค้ด

---

## Flow 1: Normal Detection → Intrusion Alert

เส้นทางที่เกิดบ่อยที่สุด — กล้องเห็นคน → AI ตรวจจับ → ละเมิดกฎ → แจ้งเตือน

```mermaid
sequenceDiagram
    participant CAM  as IP Camera
    participant BUF  as FrameBuffer
    participant AI   as InferenceEngine
    participant TRK  as ObjectTracker
    participant ZM   as ZoneManager
    participant RE   as RuleEngine
    participant AM   as AlertManager
    participant SNAP as SnapshotService
    participant DB   as PostgreSQL
    participant NS   as NotificationService
    participant WS   as WebSocket Hub

    CAM  ->> BUF  : push Frame (cam_id=3, t=T0)
    Note over BUF : deque(maxlen=1) → ทิ้งเฟรมเก่า

    AI   ->> BUF  : get_latest(cam_id=3)
    BUF  -->> AI  : Frame (pixels, t=T0)

    AI   ->> AI   : resize → 640×640, normalize
    AI   ->> AI   : OpenVINO infer (~60ms)
    AI   -->> TRK : [Detection(person, conf=0.91, bbox)]

    TRK  ->> TRK  : ByteTrack.update(detections)
    TRK  -->> RE  : [Track(id=42, person, bbox, dwell=0s)]

    RE   ->> ZM   : get_active_zones(cam_id=3)
    ZM   -->> RE  : [Zone(id=7, polygon, rule=INTRUSION)]

    RE   ->> RE   : zone.contains(track.centroid) → TRUE
    RE   ->> RE   : rule.is_scheduled_now() → TRUE (22:00-06:00)
    RE   -->> AM  : Event(INTRUSION, cam=3, zone=7, track=42)

    AM   ->> AM   : check Redis key "cd:3:7:42:intrusion"
    AM   -->> AM  : KEY NOT FOUND → proceed

    AM   ->> SNAP : save_snapshot(frame, [track], zone)
    SNAP -->> AM  : "/snapshots/2026/05/07/ev_1234.jpg"

    AM   ->> DB   : INSERT events (is_alerted=True)
    DB   -->> AM  : event_id=1234

    AM   ->> NS   : send_alert(AlertPayload)
    NS   ->> NS   : send_line(payload, snapshot_path)
    NS   ->> NS   : send_webhook(payload)
    NS   ->> DB   : INSERT notifications (status=sent)

    AM   ->> AM   : Redis SETEX "cd:3:7:42:intrusion" 300

    AM   ->> WS   : broadcast AlertMessage(event_id=1234)
    WS   ->> WS   : push to all connected Dashboard clients
```

**จุดที่ต้องระวัง:**
- ขั้นตอน SNAP → DB → NS → Redis ทำใน async coroutine — ไม่ block AI thread
- ถ้า LINE API timeout → บันทึก notification status=failed, retry ใน background

---

## Flow 2: Loitering Detection (Time-accumulation)

Loitering ต่างจาก Intrusion ตรงที่ไม่ trigger ทันที — ต้องสะสมเวลา

```mermaid
sequenceDiagram
    participant TRK  as ObjectTracker
    participant RE   as RuleEngine
    participant AM   as AlertManager

    Note over TRK,AM: Frame T=0 — Track 55 เข้า Zone ATM

    TRK  -->> RE : Track(id=55, in_zone=True, dwell=0s)
    RE   ->> RE  : dwell(0) < threshold(180s) → no event

    Note over TRK,AM: Frame T=60s — ยังอยู่ใน Zone

    TRK  -->> RE : Track(id=55, in_zone=True, dwell=60s)
    RE   ->> RE  : dwell(60) < 180 → no event

    Note over TRK,AM: Frame T=180s — ครบเวลา!

    TRK  -->> RE : Track(id=55, in_zone=True, dwell=182s)
    RE   ->> RE  : dwell(182) >= 180 → CREATE Event(LOITERING)
    RE   -->> AM : Event(LOITERING, track=55, dwell=182s)
    AM   ->> AM  : cooldown check → not found → ALERT

    Note over TRK,AM: Frame T=240s — ยังอยู่ใน Cooldown

    TRK  -->> RE : Track(id=55, in_zone=True, dwell=242s)
    RE   ->> RE  : dwell >= threshold → CREATE Event(LOITERING)
    RE   -->> AM : Event(LOITERING, track=55)
    AM   ->> AM  : cooldown check → FOUND → SUPPRESS

    Note over TRK,AM: Frame T=260s — ออกจาก Zone

    TRK  -->> RE : Track(id=55, in_zone=False)
    RE   ->> RE  : reset dwell_time[55] = 0

    Note over TRK,AM: Frame T=320s — กลับเข้ามาอีก (ยังใน cooldown)

    TRK  -->> RE : Track(id=55, in_zone=True, dwell=10s)
    RE   ->> RE  : dwell(10) < 180 → no event
```

**Key Implementation Detail:**

```python
# dwell_time เป็น property ของ Track ที่สะสมเฉพาะตอนอยู่ใน zone นั้น
# ถ้าออกจาก zone → reset dwell สำหรับ zone นั้น
# ถ้า track หาย (lost) → reset ทุก zone

class DwellTracker:
    def __init__(self):
        self._dwell: dict[tuple[int,int], float] = {}
        # key = (track_id, zone_id), value = accumulated seconds

    def update(self, track_id, zone_id, in_zone: bool, dt: float):
        key = (track_id, zone_id)
        if in_zone:
            self._dwell[key] = self._dwell.get(key, 0.0) + dt
        else:
            self._dwell.pop(key, None)
        return self._dwell.get(key, 0.0)
```

---

## Flow 3: Camera Disconnect & Reconnect

ทดสอบว่าระบบ Resilient จริงไหม — กล้องดับแล้วฟื้นคืนมา

```mermaid
sequenceDiagram
    participant CAM  as IP Camera (Cam-03)
    participant ING  as CameraThread-03
    participant BUF  as FrameBuffer
    participant AI   as AI Thread
    participant DB   as PostgreSQL
    participant WS   as WebSocket Hub

    Note over CAM,WS: ปกติ — ทุกอย่างทำงาน

    CAM  ->> ING  : RTSP stream (OK)
    ING  ->> BUF  : push Frame

    Note over CAM,ING: กล้องดับ / สาย LAN หลุด

    CAM  --x ING  : stream disconnected
    ING  ->> ING  : cap.read() returns False
    ING  ->> ING  : cap.release()
    ING  ->> DB   : INSERT camera_status(cam=3, status='offline')
    ING  ->> WS   : broadcast {"type":"camera_offline","camera_id":3}

    loop Exponential Backoff (1s, 2s, 4s, 8s, ... max 30s)
        ING  ->> ING  : sleep(backoff)
        ING  ->> CAM  : cv2.VideoCapture(rtsp_url) attempt
        CAM  --x ING  : failed (ยังดับอยู่)
    end

    Note over CAM,ING: กล้องกลับมา

    ING  ->> CAM  : cv2.VideoCapture(rtsp_url) attempt
    CAM  -->> ING : RTSP stream (OK)
    ING  ->> DB   : UPDATE cameras SET status='online'
    ING  ->> WS   : broadcast {"type":"camera_online","camera_id":3}
    ING  ->> BUF  : push Frame (กลับมาทำงานปกติ)

    Note over AI,BUF: AI Thread ไม่สนใจเลย — ดึง None จาก BUF → ข้ามกล้องนั้น
    AI   ->> BUF  : get_latest(cam_id=3) → None (ช่วงที่ดับ)
    AI   ->> AI   : skip cam_id=3 → proceed to cam_id=4
```

---

## Flow 4: Admin กำหนด Zone และ Rule ใหม่ผ่าน Web UI

```mermaid
sequenceDiagram
    actor ADMIN  as Admin (Web Browser)
    participant UI  as React Dashboard
    participant API as FastAPI
    participant DB  as PostgreSQL
    participant ZM  as ZoneManager (in-memory)
    participant RE  as RuleEngine

    ADMIN ->> UI  : วาด Polygon บนภาพกล้อง
    UI    ->> UI  : เก็บ coordinates [[x,y],...]
    ADMIN ->> UI  : กรอกชื่อโซน, เลือก Rule Type, ตั้ง Threshold
    ADMIN ->> UI  : กด "Save Zone & Rule"

    UI    ->> API : POST /api/zones/ {camera_id, name, coords, ...}
    API   ->> API : validate coordinates (≥3 points, closed polygon)
    API   ->> DB  : INSERT zones → zone_id=15
    API   -->> UI : {zone_id: 15, status: "created"}

    UI    ->> API : POST /api/rules/ {zone_id:15, type:"loitering", threshold:180, ...}
    API   ->> DB  : INSERT rules → rule_id=22
    API   ->> ZM  : reload_zones(camera_id=3)
    ZM    ->> DB  : SELECT zones+rules WHERE camera_id=3 AND is_active
    DB    -->> ZM : [zone_id=15, rule_id=22, ...]
    ZM    ->> ZM  : update in-memory cache

    API   -->> UI : {rule_id: 22, status: "created"}
    UI    ->> ADMIN : แสดง "Zone saved. Active immediately."

    Note over RE,ZM: รอบ inference ถัดไป
    RE    ->> ZM  : get_active_zones(cam_id=3)
    ZM    -->> RE : [..., Zone(id=15)] ← ใหม่ถูกรวมแล้ว
```

**ทำไม Reload ทันที ไม่รอ restart:**
Zone Manager เก็บ cache in-memory และ reload เมื่อ API สั่ง
ทำให้ Admin สามารถ fine-tune กฎ แล้วเห็นผลทันทีโดยไม่ต้อง restart service

---

## Flow 5: LPR — ตรวจสอบทะเบียนรถ

```mermaid
sequenceDiagram
    participant TRK  as ObjectTracker
    participant RE   as RuleEngine
    participant LPR  as LPREngine
    participant WL   as WhitelistService
    participant AM   as AlertManager
    participant DB   as PostgreSQL

    TRK  -->> RE  : Track(id=77, class="car", bbox, in_lpr_zone=True)

    RE   ->> RE   : Zone type = LPR_CHECK
    RE   ->> LPR  : detect_plate(crop_image(frame, bbox))

    LPR  ->> LPR  : run plate_detector_openvino
    LPR  ->> LPR  : crop plate region
    LPR  ->> LPR  : run PaddleOCR
    LPR  -->> RE  : PlateResult(text="กข 1234", conf=0.92)

    RE   ->> WL   : is_whitelisted("กข 1234")
    WL   ->> DB   : SELECT WHERE plate='กข 1234' AND is_active AND (expires_at IS NULL OR expires_at > NOW())
    DB   -->> WL  : found: owner="นายสมชาย ใจดี"
    WL   -->> RE  : WhitelistResult(found=True, owner="นายสมชาย ใจดี")

    alt ทะเบียนอยู่ใน Whitelist
        RE   -->> RE : no event (อนุญาต)
        RE   ->> DB  : INSERT events(type='lpr_allowed', extra={plate, owner})
    else ทะเบียนไม่อยู่ใน Whitelist
        RE   -->> AM : Event(LPR_UNKNOWN, extra={plate="กข 5678", conf=0.92})
        AM   ->> AM  : cooldown check → not found
        AM   ->> DB  : INSERT events(type='lpr_unknown', is_alerted=True)
        AM   ->> AM  : send alert with plate image
    else OCR ไม่ชัด (conf < 0.7)
        RE   -->> RE : skip (ไม่แจ้งเตือน — รอเฟรมถัดไป)
    end
```

**Note:** LPR รัน **เพิ่มเติม** จาก main detection pipeline เฉพาะเมื่อมี "car" ใน LPR Zone
ไม่กระทบ throughput ของกล้องอื่น เพราะรันใน thread แยก
