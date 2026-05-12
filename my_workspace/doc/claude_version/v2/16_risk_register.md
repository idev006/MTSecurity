# 16 — Risk Register
### สำหรับทีม 1-3 คน · อัปเดตทุกสิ้น Phase

---

## วิธีใช้

```
ระดับความเสี่ยง = โอกาสเกิด × ผลกระทบ

โอกาสเกิด  : L=ต่ำ(1)  M=กลาง(2)  H=สูง(3)
ผลกระทบ   : L=น้อย(1) M=กลาง(2)  H=มาก(3)

ระดับ 7-9 = 🔴 สูง    — ต้องวางแผนก่อน implement
ระดับ 4-6 = 🟡 กลาง   — มี mitigation plan
ระดับ 1-3 = 🟢 ต่ำ    — monitor เท่านั้น

อัปเดตสถานะทุกครั้งที่: จบ Phase / เกิด incident / risk เปลี่ยน
```

---

## หมวด 1: ความเสี่ยงทางเทคนิค

| ID | ความเสี่ยง | โอกาส | ผลกระทบ | ระดับ | Mitigation | สถานะ |
|----|-----------|--------|---------|-------|-----------|--------|
| T-01 | กล้อง RTSP disconnect บ่อย (network unstable) | H | M | 🟡 6 | Auto-reconnect + exponential backoff (ออกแบบไว้ใน 13_state_machines.md) | OPEN |
| T-02 | AI false positive สูง — แจ้งเตือนบ่อยเกินไป | H | H | 🔴 9 | ปรับ confidence threshold + cooldown + motion gate ก่อนส่ง AI | OPEN |
| T-03 | AI false negative — ตรวจไม่พบคนจริง | M | H | 🟡 6 | ทดสอบกับสภาพแสงจริง, กลางคืน, มุมกล้องต่างๆ ก่อน go-live | OPEN |
| T-04 | CPU overload เมื่อกล้อง 10 ตัว trigger AI พร้อมกัน | M | H | 🟡 6 | Motion gate + AI Queue (WIP=2) + monitor CPU ใน health dashboard | OPEN |
| T-05 | Disk เต็มจาก snapshot + video clip สะสม | H | M | 🟡 6 | Auto-purge policy (30 วัน), disk monitor alert เมื่อ < 20GB | OPEN |
| T-06 | SQLite ช้าเมื่อ events table โต > 500K rows | L | M | 🟢 2 | Index ออกแบบไว้ใน 06_domain_model.md, migrate PostgreSQL เมื่อถึง 1M rows | OPEN |
| T-07 | OpenVINO model ให้ผลต่างกันบน OS ต่างกัน | L | M | 🟢 2 | ทดสอบบน Windows + Linux ก่อน release, บันทึก model version | OPEN |
| T-08 | Memory leak ใน frame buffer หรือ WebSocket | M | H | 🟡 6 | Monitor RSS memory ใน health beat, ทดสอบ 24h continuous run (Phase 6) | OPEN |
| T-09 | WebSocket drop เมื่อ Console เปิดนาน | M | M | 🟡 4 | Auto-reconnect WebSocket ใน Vue composable + แสดง "Reconnecting..." | OPEN |
| T-10 | Claude API timeout / unavailable | L | M | 🟢 2 | NLQ fallback: "ระบบ AI ไม่พร้อม กรุณาค้นหาด้วย filter แทน" | OPEN |

---

## หมวด 2: ความเสี่ยงด้าน Security

| ID | ความเสี่ยง | โอกาส | ผลกระทบ | ระดับ | Mitigation | สถานะ |
|----|-----------|--------|---------|-------|-----------|--------|
| S-01 | RTSP URL/credential รั่วไหล | M | H | 🟡 6 | เข้ารหัส AES-256 ใน DB (ออกแบบใน 08_security_guide.md) | OPEN |
| S-02 | JWT secret key อ่อนแอหรือ hardcode | M | H | 🟡 6 | บังคับ 32-byte random key, ตรวจใน startup, ไม่รับ default value | OPEN |
| S-03 | Brute force login | M | H | 🟡 6 | Rate limit 5/min per IP + account lockout หลัง 10 ครั้ง | OPEN |
| S-04 | Operator เข้าถึงกล้องที่ไม่ได้รับมอบหมาย | L | H | 🟡 3 | camera_ids scope enforce ทุก endpoint รวมถึง NLQ (ออกแบบใน 04, 15) | OPEN |
| S-05 | Snapshot/clip เข้าถึงโดยไม่มีสิทธิ์ | L | M | 🟢 2 | ทุก snapshot URL ผ่าน authenticated API ไม่ใช่ static file server | OPEN |
| S-06 | LINE/Discord token รั่วไหลใน log | M | M | 🟡 4 | ใช้ SecretStr (Pydantic), ปิด debug log ใน production | OPEN |

---

## หมวด 3: ความเสี่ยงด้านโปรเจกต์

| ID | ความเสี่ยง | โอกาส | ผลกระทบ | ระดับ | Mitigation | สถานะ |
|----|-----------|--------|---------|-------|-----------|--------|
| P-01 | Scope creep — เพิ่ม feature ระหว่าง implement | H | H | 🔴 9 | บันทึก feature ใหม่ใน backlog ก่อน อย่า implement ทันที, ทำ Phase ปัจจุบันให้เสร็จก่อน | OPEN |
| P-02 | Phase ล่าช้ากว่าแผน | M | M | 🟡 4 | Review ทุกสิ้น Phase, ลด scope ของ Phase ถัดไปถ้าจำเป็น | OPEN |
| P-03 | ความรู้ OpenVINO + ByteTrack ไม่เพียงพอ | M | H | 🟡 6 | spike 2-3 วัน ทดสอบ model inference ก่อนเริ่ม Phase 2 จริง | OPEN |
| P-04 | ทีมมีคนเดียว — ถ้าหยุดงานโครงการหยุดด้วย | H | H | 🔴 9 | เขียนเอกสาร + comment โค้ดให้ครบ, บันทึก decision ใน ADR | OPEN |
| P-05 | Claude API cost เกินงบถ้า NLQ ถูกใช้มาก | L | L | 🟢 1 | Rate limit 20 req/min/actor, monitor monthly cost, cap budget alert | OPEN |

---

## หมวด 4: ความเสี่ยงด้านการใช้งาน (Operational)

| ID | ความเสี่ยง | โอกาส | ผลกระทบ | ระดับ | Mitigation | สถานะ |
|----|-----------|--------|---------|-------|-----------|--------|
| O-01 | ไฟดับ — ระบบหยุดทำงาน | M | H | 🟡 6 | UPS สำหรับเครื่อง server + กล้อง, systemd/NSSM auto-restart | OPEN |
| O-02 | Alert fatigue — แจ้งเตือนมากเกินไป operator เพิกเฉย | H | H | 🔴 9 | ปรับ threshold + cooldown ให้เหมาะสม, ทดสอบ 1 สัปดาห์ก่อน go-live ทุกกล้อง | OPEN |
| O-03 | กล้องมุมไม่ดี — AI ตรวจไม่เจอ | M | M | 🟡 4 | ทดสอบ detection ก่อนติดตั้งถาวร, document มุมกล้องที่ดีที่สุด | OPEN |
| O-04 | แสงน้อยกลางคืน — accuracy ตก | H | M | 🟡 6 | ทดสอบกลางคืนด้วย, พิจารณา IR camera, ปรับ confidence threshold ตาม schedule | OPEN |
| O-05 | Network ช้า — Console lag | L | M | 🟢 2 | Resolution tier system รองรับ (14_streaming_performance.md), monitor bandwidth | OPEN |

---

## Risk Priority Matrix

```
ผลกระทบ
  H  │ T-02🔴  T-03🟡  T-04🟡  S-02🟡  S-03🟡  P-04🔴
     │ T-08🟡  P-03🟡  O-01🟡  O-02🔴
  M  │ T-01🟡  T-05🟡  T-06🟢  T-09🟡  S-01🟡  S-06🟡
     │ P-02🟡  O-03🟡  O-04🟡
  L  │ T-07🟢  T-10🟢  S-04🟡  S-05🟢  P-05🟢  O-05🟢
     └────────────────────────────────────────────────
          L          M          H        โอกาสเกิด
```

---

## 🔴 Risk ระดับสูง — ต้องแก้ก่อน implement

### T-02: AI False Positive สูง

```
ปัญหา   : ระบบแจ้งเตือนบ่อยเกินจนไม่น่าเชื่อถือ
แผน    :
  Phase 2: ทดสอบ confidence threshold กับวิดีโอจริง
           เริ่มที่ 0.6 ปรับขึ้นถ้า false positive มาก
  Phase 3: Motion gate — AI ทำงานเฉพาะเมื่อ motion detected
  Phase 6: ทดสอบ 1 สัปดาห์ continuous — นับ false positive rate
           เป้า: false positive < 5% ของ total alerts
```

### O-02: Alert Fatigue

```
ปัญหา   : Operator เห็น alert เยอะเกินจนเริ่มเพิกเฉย → ระบบไร้ประโยชน์
แผน    :
  Phase 3: ตั้ง cooldown ขั้นต่ำ 30 วิ per zone
  Phase 5: Console แสดง alert count / hour เพื่อ monitor
  Pre go-live: ทดสอบ 1 สัปดาห์ ถ้า alert > 20/วัน ให้ปรับ rule ก่อน
```

### P-01: Scope Creep

```
ปัญหา   : เพิ่ม feature ไปเรื่อยๆ ไม่ได้ของจริงสักที
แผน    :
  กฎ: feature ใหม่ทุกอย่าง → ใส่ backlog ก่อน
  กฎ: ไม่ implement ของใหม่จนกว่า Phase ปัจจุบันจะ done
  กฎ: review backlog ทุกสิ้น Phase เท่านั้น
```

### P-04: Bus Factor = 1 (ถ้าทำคนเดียว)

```
ปัญหา   : ถ้าคนเดียวหยุดงาน โครงการหยุด
แผน    :
  บันทึก ADR ทุก decision ที่ไม่ชัดเจน
  Comment โค้ดเฉพาะ "ทำไม" ไม่ใช่ "ทำอะไร"
  Git commit message ให้อ่านแล้วเข้าใจ
  เอกสาร V2 นี้คือ "ถ้าคนอื่นมาสาน" guide
```

---

## Timeline (จากวันนี้: 11 พ.ค. 2569)

```
Phase           ระยะเวลา    เป้าหมายเสร็จ    Milestone
────────────────────────────────────────────────────────────
Phase 1: Foundation   2 สัปดาห์   25 พ.ค. 2569   M1: Bus is alive
Phase 2: AI + Camera  3 สัปดาห์   15 มิ.ย. 2569  M2: AI sees person
Phase 3: Rules+Alert  2 สัปดาห์   29 มิ.ย. 2569  M3: LINE alert works
Phase 4: API Core     2 สัปดาห์   13 ก.ค. 2569   M4: API + Permission
Phase 5: Console      3 สัปดาห์   3 ส.ค. 2569    M5: Console live
Phase 6: Hardening    2 สัปดาห์   17 ส.ค. 2569   M6: Production ready
────────────────────────────────────────────────────────────
รวม                   14 สัปดาห์  17 ส.ค. 2569
```

> **หมายเหตุ**: Timeline สำหรับ 1 คนทำงานเต็มเวลา
> ถ้าทำ part-time → คูณ 1.5-2 เท่า
> ถ้าทีม 2-3 คน → หาร 1.3-1.5 เท่า (ไม่ใช่หาร 3 เพราะมี coordination cost)

---

## Budget Estimate

```
รายการ                              ราคา (บาท)
──────────────────────────────────────────────────
Hardware (มีอยู่แล้ว)
  เครื่อง Ryzen + 16GB RAM          0        (อัพแล้ว)
  กล้อง IP Camera × 10              0        (สมมติมีแล้ว)

Software (ฟรีทั้งหมด)
  Python + OpenVINO + OpenCV         0
  Vue + DaisyUI + Playwright         0
  SQLite                             0

API Costs (รายเดือน)
  Claude API (NLQ ~1000 queries)    ~35      (Haiku ~$1/month)
  LINE Messaging API                 0        (ฟรี 200 msg/month)
  Discord / Slack Webhook            0        (ฟรี)

Storage
  SSD 512GB (ถ้ายังไม่มี)           ~1,200
  Backup drive 1TB (แนะนำ)          ~1,500

Total เริ่มต้น                      ~2,700 บาท
Total รายเดือน                       ~35 บาท
──────────────────────────────────────────────────
เทียบกับ: ระบบ AI CCTV สำเร็จรูป  50,000-500,000 บาท
```

---

## Log การอัปเดต Risk

```
วันที่          อัปเดตโดย    รายการที่เปลี่ยน
────────────────────────────────────────────
11 พ.ค. 2569   (ทีม)         สร้าง Risk Register เริ่มต้น
               -              อัปเดตครั้งถัดไป: สิ้น Phase 1
```
