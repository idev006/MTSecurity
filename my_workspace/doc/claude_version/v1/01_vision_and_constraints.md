# 01 — Vision & Constraints

---

## 1. ปัญหาที่เราแก้

กล้องวงจรปิดแบบเดิมทำหน้าที่เดียวคือ **บันทึก** — มันไม่ได้ "ดู"
เมื่อเกิดเหตุการณ์ เจ้าหน้าที่ต้องนั่ง rewind ย้อนดูเทปทีละชั่วโมง
และที่แย่กว่านั้น ถ้าไม่มีใครมอนิเตอร์อยู่ตอนนั้น — ไม่มีใครรู้เลยว่าเกิดอะไรขึ้น

MTSecurity เปลี่ยนบทบาทของกล้องจาก **Recorder** เป็น **Observer**
ระบบดูแทนมนุษย์ตลอด 24 ชั่วโมง แล้วเตือนก็ต่อเมื่อมีบางอย่างที่ควรรู้

---

## 2. เป้าหมายหลัก (Goals)

```
G1  ตรวจจับมนุษย์ รถ สัตว์ ควัน/ไฟ แบบ Real-time จากกล้องสูงสุด 10 ตัว
G2  วิเคราะห์พฤติกรรม: บุกรุก, วนเวียน, ข้ามเส้น, แออัด, วัตถุต้องสงสัย
G3  แจ้งเตือนภายใน 3 วินาทีหลังเหตุการณ์เกิดขึ้น ผ่าน LINE / Email / Webhook
G4  บันทึก Event + Snapshot ทุกครั้ง ให้ค้นหาย้อนหลังได้
G5  ทำงานได้บน CPU-only Hardware (Ryzen 7 5700G) โดยไม่ต้องการ GPU
G6  ผู้ดูแลระบบกำหนดโซนและกฎผ่าน Web UI ได้โดยไม่ต้องแก้โค้ด
```

---

## 3. สิ่งที่ไม่ทำ (Non-Goals)

สิ่งเหล่านี้ **ไม่อยู่ใน Scope** — ระบุไว้เพื่อป้องกันการขยาย Scope โดยไม่ตั้งใจ:

```
NG1  ไม่ทำ Facial Recognition (จดจำใบหน้าบุคคล) — ข้อกังวลด้าน Privacy & กฎหมาย
NG2  ไม่ทำ Continuous 24/7 Video Recording — ออกแบบให้บันทึกเฉพาะ Event
NG3  ไม่ทำ Cloud-dependent Infrastructure — ระบบต้องทำงาน Offline ได้ 100%
NG4  ไม่ทำ Mobile App Native — ใช้ LINE Notify + Web Dashboard เป็น Client
NG5  ไม่รองรับกล้องมากกว่า 10 ตัวในเวอร์ชัน CPU-only — ต้องเพิ่ม Hardware ก่อน
NG6  ไม่ทำ Predictive Analytics หรือ ML Training Pipeline ในระบบนี้
```

---

## 4. ข้อจำกัดแข็ง (Hard Constraints)

ข้อจำกัดเหล่านี้เป็น **ข้อเท็จจริงที่เปลี่ยนแปลงไม่ได้** ทุกการตัดสินใจต้องเคารพสิ่งเหล่านี้:

### HC-1: Hardware Budget
```
CPU  : AMD Ryzen 7 5700G (8c/16t, 3.8GHz)
RAM  : 16 GB DDR4
GPU  : ไม่มี (iGPU Vega 8 ใช้ได้จำกัด)
Disk : SSD 512 GB
NIC  : 1Gbps
```
**ผลกระทบต่อการออกแบบ:**
- ใช้ OpenVINO + INT8 quantization เพื่อ inference บน CPU
- โมเดลต้องมีขนาด ≤ 50MB (RAM budget)
- วนลูปกล้องแบบ Round-robin ด้วย Thread เดียว ไม่ spawn thread ต่อกล้อง

### HC-2: Network Environment
```
กล้อง IP Camera   : RTSP over LAN (VLAN แยก)
Bandwidth เข้า    : ~150 Mbps รวมทุกกล้อง (15 Mbps/cam × 10)
Bandwidth ออก     : Internet 50 Mbps (สำหรับ LINE/Email)
```
**ผลกระทบต่อการออกแบบ:**
- Decode ที่ Server ไม่ใช่ที่กล้อง — ดึง RTSP stream โดยตรง
- Snapshot ที่ส่ง LINE ต้อง resize เหลือ ≤ 300KB

### HC-3: Latency Requirement
```
Detection-to-Alert  : ≤ 3 วินาที (วัดจากเวลากล้องจับภาพถึงแจ้งเตือนส่งออก)
Dashboard Refresh   : ≤ 1 วินาที (WebSocket frame push)
```
**ผลกระทบต่อการออกแบบ:**
- Inference ต้องเสร็จใน ≤ 80ms ต่อเฟรม
- Alert pipeline ต้องเป็น async ไม่ block AI thread

### HC-4: Data Retention Policy
```
Event Snapshots  : เก็บ 90 วัน แล้ว auto-purge
Event Metadata   : เก็บ 365 วัน
Video Clips      : เก็บ 30 วัน (เฉพาะ clip ที่ผูกกับ Alert)
```

---

## 5. Quality Attributes (คุณภาพที่คาดหวัง)

| คุณภาพ | เป้าหมาย | วิธีวัด |
|--------|---------|--------|
| **Availability** | 99.5% uptime (≤ 44 ชม./ปีที่ยอมรับการหยุด) | Health check endpoint |
| **Detection Recall** | ≥ 90% สำหรับ "person" กลางวัน | ทดสอบด้วย benchmark dataset |
| **False Positive Rate** | ≤ 5 alerts ผิดพลาดต่อกล้องต่อวัน | Log + manual review |
| **Alert Latency (P95)** | ≤ 3 วินาที | Timestamp เปรียบเทียบ |
| **System RAM Usage** | ≤ 8 GB ขณะ 10 กล้องทำงาน | `psutil` monitoring |
| **Throughput** | ≥ 1 FPS ต่อกล้อง (effective AI FPS) | Inference counter |

---

## 6. ผู้ใช้งานระบบ (Stakeholders)

```
[รปภ. / เจ้าหน้าที่หน้างาน]
  → ดู Dashboard real-time
  → รับ LINE Notify เมื่อเกิดเหตุ
  → ค้นหาภาพเหตุการณ์ย้อนหลัง

[ผู้ดูแลระบบ (Admin)]
  → กำหนดกล้อง, โซน, กฎ ผ่าน Web UI
  → จัดการ Whitelist (LPR)
  → ดู Analytics รายวัน/รายสัปดาห์

[เจ้าของ / ผู้บริหาร]
  → รับ Daily Summary Email
  → ดู Heat Map และสถิติรวม
```

---

## 7. ความเสี่ยงและแผนรองรับ

| ความเสี่ยง | โอกาส | ผลกระทบ | แผนรองรับ |
|-----------|-------|---------|-----------|
| CPU overload เมื่อกล้อง 10 ตัวทำงานพร้อมกัน | สูง | กลาง | Frame dropping + ปรับ FPS target ต่อกล้อง |
| RTSP stream หลุดบ่อย | กลาง | ต่ำ | Auto-reconnect loop with exponential backoff |
| กล้องกลางคืนคุณภาพต่ำ | กลาง | กลาง | ปรับ confidence threshold ตามเวลา (schedule) |
| LINE API rate limit | ต่ำ | ต่ำ | Cooldown + queue burst protection |
| Disk เต็มจาก Snapshots | ต่ำ | สูง | Auto-purge cron job + disk usage alert |
