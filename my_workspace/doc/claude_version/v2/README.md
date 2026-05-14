# MTSecurity v2 — Architecture Documentation
### Multitier · API-as-Core · Communication-Driven Design

---

## Environment (Confirmed)

```
Python      : 3.12.10
Venv        : D:\dev\MTSecurity\my_env\
Project     : D:\dev\MTSecurity\my_workspace\
Pre-installed: openvino 2026.1.0, numpy 2.4.4
Frontend    : Vue 3 + TypeScript + DaisyUI
Testing     : pytest (backend) · Playwright (E2E) · Vitest (frontend)
```

---

## สิ่งที่เปลี่ยนจาก v1

| v1 (เดิม) | v2 (ใหม่) |
|-----------|----------|
| 4-Layer pipeline (linear) | 7-Layer OSI-inspired (strict boundary) |
| API = presentation layer (ปลายสุด) | **API = Core** (ศูนย์กลางทุก communication) |
| Component คุยกันโดยตรง | ทุก message ผ่าน **Message Bus** |
| Config กระจายในแต่ละ service | **SSOT** — ConfigService เป็น single source |
| User = Admin เท่านั้น | **Actor Model** — 6 actors, ใช้งานต่างกัน |
| Dashboard = ดูภาพ + log | **Pilot's Console** — command center |
| ไม่มี protocol กลาง | **MTP** (MTSecurity Transport Protocol) |

---

## Concept Map

```
                    ┌─────────────────────────────────────┐
                    │         PILOT'S CONSOLE              │
                    │   (Master Control — All Actors)      │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │            API CORE                  │
                    │   REST · WebSocket · MTP Bus         │
                    └──┬──────────┬──────────┬────────────┘
                       │          │          │
          ┌────────────▼─┐  ┌─────▼──────┐  ┌▼────────────┐
          │   INGESTION  │  │    AI +    │  │    ALERT    │
          │   LAYER      │  │   RULES    │  │   ENGINE    │
          └──────────────┘  └────────────┘  └─────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │              SSOT                    │
                    │  ConfigService · StateRegistry       │
                    └─────────────────────────────────────┘
```

---

## ดัชนีเอกสาร

| ไฟล์ | เนื้อหา |
|------|--------|
| `01_architecture_manifesto.md` | ปรัชญา + 7-Layer + API-as-Core |
| `02_communication_arch.md` | MTP Protocol + Message Bus + Event Schema |
| `03_ssot_config.md` | SSOT Design + ConfigService + Change Propagation |
| `04_actors_usecases.md` | 6 Actors + Use Cases + Permission Matrix |
| `05_pilots_console.md` | Pilot's Console — Layout, Widgets, Actions |
| `06_domain_model.md` | Updated Domain Model + SQLAlchemy ORM |
| `07_module_structure.md` | Final Python Module Layout |
| `08_security_guide.md` | Secrets Management + TLS + Auth Flows + Input Validation |
| `09_api_reference.md` | REST Endpoints + Request/Response + Error Codes + WebSocket |
| `10_tech_stack.md` | Tech Choices + OS Support + pyproject.toml + Hardware + ADR |
| `11_development_guide.md` | Kanban + XP + Phases + DoD + Cross-OS Setup |
| `12_sequence_diagrams.md` | 5 Key Flows: Detection→Alert, Config Change, Auth, Reconnect, ACK |
| `13_state_machines.md` | Camera · Alert · Rule Schedule · Boot · OS Service Lifecycle |
| `14_streaming_performance.md` | 10-Camera No-Lag · Resolution Tiers · Canvas Overlay · WebSocket |
| `15_nlq_design.md` | Natural Language Query · Claude API · RAG over Events |
| `16_risk_register.md` | Risk Register · Timeline · Budget · อัปเดตทุกสิ้น Phase |
| `17_test_audit_plan.md` | Test Plan · Playwright E2E · Vitest · pytest |
| `18_uiux_overhaul.md` | World-Class UI/UX Overhaul · Mission Control Aesthetic · Theme System · Toast Store |

---

## อ่านตามลำดับนี้

```
01 → 02 → 03     ← เข้าใจ architecture ก่อน
04               ← กำหนด who can do what
05               ← ออกแบบ UX สำหรับ actor
10               ← ตกลง tech stack + OS support + ADR (ก่อนเขียน code)
08               ← วางแผน security (Critical — ทำก่อน implement)
09               ← ตกลง API contract กับ Frontend
12               ← เข้าใจ flow ก่อน implement (sequence diagrams)
13               ← เข้าใจ state ของ Camera + Alert + Boot
11               ← ดู development phases + Kanban + XP + cross-OS setup
06 → 07          ← ลงมือสร้าง
```
