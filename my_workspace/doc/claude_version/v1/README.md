# MTSecurity — AI-Powered Video Management System
### ดัชนีเอกสารโครงการ (Claude's Edition)

---

## ทำไมถึงต้องมีเอกสารชุดนี้

เอกสารชุดนี้เขียนขึ้นด้วยหลักการ **"อธิบายว่าทำไม ไม่ใช่แค่ทำอะไร"**
ทุกการตัดสินใจในการออกแบบมีเหตุผลรองรับ ทุกการ trade-off ถูกระบุชัดเจน
เพื่อให้ทีมที่อ่านสามารถตัดสินใจได้ถูกต้องเมื่อเจอสถานการณ์ที่เอกสารยังไม่ครอบคลุม

---

## โครงสร้างเอกสาร

```
claude_version/
├── README.md                    ← คุณอยู่ที่นี่ (ดัชนีและหลักการ)
├── 01_vision_and_constraints.md ← เป้าหมาย, สิ่งที่ไม่ทำ, ข้อจำกัดแข็ง
├── 02_architecture.md           ← สถาปัตยกรรมระบบ 4 Layer
├── 03_domain_model.md           ← Class Diagram, DB Schema, Data Contracts
├── 04_key_flows.md              ← Sequence Diagrams เส้นทางวิกฤต 5 เส้นทาง
├── 05_technology_stack.md       ← การเลือก Technology พร้อมเหตุผล
└── 06_module_structure.md       ← โครงสร้าง Python Codebase
```

---

## อ่านตามลำดับนี้

| ถ้าคุณเป็น... | เริ่มที่... |
|---------------|------------|
| Product Owner / ผู้บริหาร | `01` → `README` |
| Software Architect | `01` → `02` → `03` → `05` |
| Backend Developer | `02` → `06` → `04` → `03` |
| DevOps / Infra | `02` → `05` → `06` |
| ใหม่กับโปรเจกต์ | อ่านตามลำดับ `01` → `06` |

---

## หลักการออกแบบ (Design Principles)

ระบบนี้ถูกออกแบบโดยยึดหลัก 5 ข้อ ซึ่งทุกการตัดสินใจต้องอ้างอิงกลับมาที่หลักการเหล่านี้:

### 1. CPU-First, GPU-Ready
ฮาร์ดแวร์เริ่มต้นคือ Ryzen 7 5700G ไม่มี GPU
ดังนั้นทุกการเลือก Model, Library, และ Pipeline
ต้องทำงานได้ดีบน CPU ก่อน และเปลี่ยนไป GPU ได้โดยแก้ config เพียงบรรทัดเดียว

### 2. Decouple Everything
แต่ละ Service ต้องทำงานได้โดยไม่พังพร้อมกันทั้งระบบ
กล้องตัวที่ 3 ดับ → AI ยังวนต่อ, Alert ยังส่งได้, Dashboard ยังดูได้
ทำได้โดยใช้ Queue เป็นตัวกลางระหว่าง Layer เสมอ

### 3. Latency Over Accuracy (ในบริบท Real-time)
ระบบนี้คือ Security — ผู้ใช้ต้องการ **เห็นเหตุการณ์เร็ว**
ยอมให้ False Positive บ้าง ดีกว่าแจ้งเตือนช้า
ดังนั้น Frame Dropping เป็น Feature ไม่ใช่ Bug

### 4. Events, Not Video
บันทึกเฉพาะ **Event Metadata + Snapshot**
ไม่บันทึก Video 24/7 ต่อเนื่อง (ใช้ storage มหาศาล, หา needle ใน haystack ยาก)
Video Clip 10 วินาทีบันทึกเฉพาะเมื่อ Alert เกิดขึ้นเท่านั้น

### 5. Alert Fatigue คือศัตรู
ระบบที่แจ้งเตือนมากเกินไปคือระบบที่ไม่มีใครใช้
ทุก Alert ต้องผ่าน Debounce + Cooldown
กฎทุกข้อต้องมี `cooldown_seconds` เป็น required field ไม่ใช่ optional

---

## Glossary (นิยามคำสำคัญ)

| คำ | นิยาม |
|----|-------|
| **Frame** | ภาพ 1 เฟรมจากกล้อง ณ เวลาหนึ่ง |
| **Detection** | วัตถุ 1 ชิ้นที่ AI ตรวจพบในเฟรมเดียว (ยังไม่มี ID) |
| **Track / TrackedObject** | วัตถุที่ถูก Tracker ผูก ID แล้ว มีประวัติข้ามเฟรม |
| **Zone** | พื้นที่หรือเส้นสมมติบนหน้าจอกล้อง |
| **Rule** | เงื่อนไขที่ผูกระหว่าง Zone + ประเภทวัตถุ + พฤติกรรม |
| **Event** | เหตุการณ์ที่เกิดขึ้นเมื่อ Track ละเมิด Rule |
| **Alert** | Event ที่ผ่าน Debounce แล้ว พร้อมส่งแจ้งเตือน |
| **ROI** | Region of Interest — Zone แบบ Polygon |
| **Tripwire** | Zone แบบเส้น มีทิศทาง |
| **Dwell Time** | เวลาสะสมที่ Track อยู่ใน Zone |
| **Cooldown** | ช่วงเวลาหลัง Alert ที่ระบบจะไม่ส่งซ้ำสำหรับ Track เดิม |
