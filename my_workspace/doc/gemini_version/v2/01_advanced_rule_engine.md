# 01 — Advanced Rule Engine (Logical Security Framework)

## 1. Vision & Strategy
เป้าหมายคือการเปลี่ยนจาก "Static Rules" (ถ้าเจอคนในโซน 1 ให้แจ้งเตือน) ไปสู่ "Dynamic Security Policies" ที่ยืดหยุ่นและรองรับความต้องการที่ซับซ้อนของผู้ใช้ โดยใช้หลักการ **Combinatorial Logic (AND/OR)**

---

## 2. The Four Pillars (องค์ประกอบหลัก 4 ประการ)

เพื่อให้ระบบมีความครอบคลุม เราจะแบ่งเงื่อนไขออกเป็น 4 มิติ:

### 2.1 Time (ห้วงวัน-เวลา)
*   **Daily Schedule:** ระบุช่วงเวลาในแต่ละวัน (เช่น 08:00 - 17:00)
*   **Day of Week:** เลือกวันทำงาน หรือวันหยุด (เช่น Mon-Fri หรือ Sat-Sun)
*   **Special Dates:** วันหยุดนักขัตฤกษ์ หรือช่วงเวลาพิเศษ

### 2.2 Space (พื้นที่เฝ้าระวัง)
*   **Zones:** พื้นที่ Polygon (ROI)
*   **Tripwires:** เส้นสมมติ (Line Crossing)
*   **Multi-Zone Interaction:** การข้ามจากโซน A ไปยังโซน B

### 2.3 Object (วัตถุเป้าหมาย)
*   **Class:** บุคคล (Person), รถยนต์ (Car), รถจักรยานยนต์ (Motorcycle)
*   **Attributes:** ทะเบียนรถ (License Plate), สีเสื้อผ้า, การใส่หมวกนิรภัย
*   **Whitelist/Blacklist:** การเทียบค่ากับฐานข้อมูล (เช่น ทะเบียนรถที่ได้รับอนุญาต)

### 2.4 Behavior (พฤติกรรมเฝ้าระวัง)
*   **Intrusion:** การก้าวเข้าสู่พื้นที่
*   **Loitering:** การแช่อยู่ในพื้นที่นานเกินกำหนด (Dwell Time)
*   **Line Crossing:** การข้ามเส้นในทิศทางที่กำหนด
*   **Density:** การรวมตัวกันของคนหนาแน่น (Crowd Detection)

---

## 3. Logical Connectivity (AND / OR Framework)

ระบบจะอนุญาตให้ผู้ใช้สร้าง "Logical Blocks" เพื่อเชื่อมโยงองค์ประกอบเข้าด้วยกัน:

### ตัวอย่างการใช้งาน (Use Case Samples)

| Scenario | Logic Expression | Severity |
|----------|------------------|----------|
| **ห้ามเข้าพื้นที่ตอนกลางคืน** | `(Time: Night)` **AND** `(Space: Internal Store)` **AND** `(Object: Person)` | **CRITICAL** |
| **รถแปลกปลอมจอดแช่** | `(Object: Car)` **AND** `(Behavior: Loitering > 5m)` **AND** `NOT (Object: Whitelisted Plate)` | **HIGH** |
| **การบุกรุกหรือพยายามงัดแงะ** | `(Space: Fence)` **AND** `(Behavior: Intrusion OR Line Crossing)` | **HIGH** |

---

## 4. Implementation Roadmap

### Phase 1: Data Model (Schema Update)
*   ออกแบบตาราง `rules` ใหม่ให้เก็บเงื่อนไขแบบ JSON (Expression Tree)
*   รองรับโครงสร้าง Nested Logic

### Phase 2: System Actor (Inference & Evaluation)
*   อัปเกรด `RuleEngine` ให้สามารถ Parse Logic Tree ได้
*   เพิ่มสถานะ "Persistent State" สำหรับ Behavior เช่น Loitering

### Phase 3: Visual Rule Builder (Frontend)
*   สร้าง UI แบบ Block-based หรือ Form-based ที่เข้าใจง่าย
*   มีระบบ "Rule Simulation" เพื่อทดสอบกฎก่อนใช้งานจริง

---

## 5. Audit & Compliance
ทุกครั้งที่มีการแก้ไขกฎ ระบบจะต้องบันทึกใน **Audit Log** ตามมาตรฐานในเอกสาร `04 — Actors & Use Cases` เพื่อให้ Auditor สามารถตรวจสอบย้อนหลังได้ว่าใครเป็นคนเปลี่ยนเงื่อนไขการรักษาความปลอดภัย
