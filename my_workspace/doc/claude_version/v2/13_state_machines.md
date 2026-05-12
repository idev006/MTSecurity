# 13 — State Machines
### Camera Lifecycle · Alert Lifecycle · Rule Schedule · System Boot

---

## 1. Camera State Machine

### States และ Transitions

```
                         ┌─────────────────────────────────────────┐
                         │              CAMERA STATES               │
                         └─────────────────────────────────────────┘

                              [system start / camera added]
                                           │
                                           ▼
                              ┌────────────────────────┐
                              │        INACTIVE         │
                              │  is_active = false      │
                              │  ไม่พยายาม connect      │
                              └────────────┬────────────┘
                                           │ Admin: enable camera
                                           ▼
    ┌────────────────────────────────────────────────────────────────────┐
    │                          CONNECTING                                 │
    │  กำลัง VideoCapture(rtsp_url)    reconnect_count += 1             │
    └─────────────┬───────────────────────────────────────┬──────────────┘
                  │ connection OK                          │ timeout / refused
                  ▼                                        ▼
    ┌─────────────────────────┐              ┌─────────────────────────┐
    │         ONLINE          │              │          ERROR           │
    │  fps_actual > 0         │              │  reconnect_count > 0    │
    │  frames flowing         │              │  last_error logged       │
    │  motion detection ON    │◄─────────────│  backoff timer running   │
    └─────────────┬───────────┘  reconnect   └─────────┬───────────────┘
                  │ read error                          │ reconnect_count > 10
                  │ connection lost                     ▼
                  │                        ┌─────────────────────────┐
                  │                        │     FAILED (terminal)    │
                  │                        │  ต้อง Admin intervention │
                  │                        │  HEALTH_BEAT degraded    │
                  │                        └─────────────────────────┘
                  │
                  ▼
    ┌─────────────────────────┐
    │       RECONNECTING      │
    │  brief disconnect       │◄──────────────────────────────────────┐
    │  auto retry in 5s       │                                        │
    └─────────────┬───────────┘                                        │
                  │ success                                            │
                  └───────────────────────────────────────────────────┘
                    reconnect (back to ONLINE)
```

### State Definition (Code)

```python
# ssot/state_registry.py
from enum import Enum

class CameraStatus(str, Enum):
    INACTIVE      = "inactive"      # is_active=False ใน config
    CONNECTING    = "connecting"    # กำลัง VideoCapture()
    ONLINE        = "online"        # frames flowing
    RECONNECTING  = "reconnecting"  # connection dropped, auto retry
    ERROR         = "error"         # retry น้อยกว่า max
    FAILED        = "failed"        # retry เกิน max — ต้องการ manual fix

# State transitions ที่ valid
VALID_TRANSITIONS: dict[CameraStatus, list[CameraStatus]] = {
    CameraStatus.INACTIVE:      [CameraStatus.CONNECTING],
    CameraStatus.CONNECTING:    [CameraStatus.ONLINE, CameraStatus.ERROR],
    CameraStatus.ONLINE:        [CameraStatus.RECONNECTING, CameraStatus.INACTIVE],
    CameraStatus.RECONNECTING:  [CameraStatus.ONLINE, CameraStatus.ERROR],
    CameraStatus.ERROR:         [CameraStatus.CONNECTING, CameraStatus.FAILED],
    CameraStatus.FAILED:        [CameraStatus.CONNECTING],   # Admin retry
}
```

### Reconnect Backoff Strategy

```python
# ingestion/camera_thread.py
BACKOFF_SECONDS = [5, 10, 20, 40, 60, 60, 60]   # max 60s per retry
MAX_RETRIES = 10

def get_backoff(reconnect_count: int) -> float:
    idx = min(reconnect_count, len(BACKOFF_SECONDS) - 1)
    return BACKOFF_SECONDS[idx]

# reconnect_count=0 → wait 5s
# reconnect_count=3 → wait 40s
# reconnect_count=6+ → wait 60s
```

### MTP Messages per State Change

```
INACTIVE → CONNECTING    : (no message — internal)
CONNECTING → ONLINE      : publish CAMERA_CONNECTED
ONLINE → RECONNECTING    : publish CAMERA_DISCONNECTED
RECONNECTING → ONLINE    : publish CAMERA_CONNECTED
ERROR → FAILED           : publish HEALTH_BEAT{status="error", cam_id=X}
```

---

## 2. Alert Lifecycle State Machine

### States และ Transitions

```
                    [RULE_TRIGGERED + pass debounce]
                                 │
                                 ▼
             ┌───────────────────────────────────┐
             │              NEW                   │
             │  is_acknowledged = false           │
             │  silenced_until = null             │
             │  แสดงใน Alert Queue (สีแดง/เหลือง) │
             │  LINE Notify / Webhook ถูกส่งแล้ว  │
             └────┬──────────────┬────────────────┘
                  │              │
          Operator │ACK           │ Operator SILENCE(N min)
                  │              │
                  ▼              ▼
    ┌─────────────────┐  ┌───────────────────────┐
    │  ACKNOWLEDGED   │  │       SILENCED          │
    │  is_ack = true  │  │  silenced_until = T+N   │
    │  ack_by = user  │  │  ไม่แสดงใน queue        │
    │  ack_at = now   │  │  cooldown extend ด้วย   │
    │  note saved     │  └──────────┬──────────────┘
    └────┬────────────┘             │ silence expires
         │                          │ (new alert ใน zone เดิม)
         │ Operator ESCALATE         ▼
         ▼                 ┌──────────────────┐
    ┌─────────────────┐    │       NEW         │ ← กลับมา NEW
    │   ESCALATED     │    │  (new event_id)   │
    │  notification   │    └──────────────────┘
    │  ถูกส่งให้      │
    │  supervisor     │
    │  via LINE/email │
    └─────────────────┘
```

### Alert State ใน DB

```python
# models/event.py
class Event(Base):
    # State fields
    is_acknowledged:  Mapped[bool]           = mapped_column(default=False)
    acknowledged_by:  Mapped[int | None]     = mapped_column(ForeignKey("users.id"))
    acknowledged_at:  Mapped[datetime | None]
    silenced_until:   Mapped[datetime | None]
    is_escalated:     Mapped[bool]           = mapped_column(default=False)
    escalated_by:     Mapped[int | None]     = mapped_column(ForeignKey("users.id"))
    escalated_at:     Mapped[datetime | None]

    @property
    def current_state(self) -> str:
        if self.is_escalated:
            return "escalated"
        if self.is_acknowledged:
            return "acknowledged"
        if self.silenced_until and datetime.utcnow() < self.silenced_until:
            return "silenced"
        return "new"

    @property
    def is_active(self) -> bool:
        return self.current_state == "new"
```

### Cooldown vs Silence

```
Cooldown (Rule-level):
  กำหนดใน Rule config (cooldown_sec)
  ทำงานใน AlertManager TTLCache
  ป้องกันไม่ให้ RULE_TRIGGERED ยิงถี่เกิน
  เป็น automatic — ไม่ต้องการ human action

Silence (Alert-level):
  Operator กด [SILENCE 15m]
  บันทึกใน Event.silenced_until
  ซ่อน alert จาก queue ชั่วคราว
  เป็น human decision — มีใน audit log
```

---

## 3. Rule Schedule State Machine

```
                    [Rule config: always_on = false]
                                 │
                      ┌──────────┴──────────┐
                      │                     │
                 time_from              not in schedule
                 reached                    │
                      │                     ▼
                      ▼          ┌────────────────────┐
           ┌────────────────────┐│      INACTIVE       │
           │       ACTIVE        ││  rule ไม่ evaluate  │
           │  evaluate rules     ││  tracks             │
           │  ต่อทุก TRACK_UPDATE│└─────────┬──────────┘
           └──────────┬──────────┘          │
                      │         time_from reached
                 time_to                    │
                 reached                    │
                      └──────────►──────────┘

[Rule: always_on = true]
  → ข้าม schedule check ทั้งหมด → always ACTIVE
```

### Schedule Implementation

```python
# rules/schedule_manager.py
from datetime import datetime, time
from zoneinfo import ZoneInfo

class ScheduleManager:
    def is_rule_active(self, rule) -> bool:
        if rule.always_on:
            return True

        now = datetime.now(ZoneInfo("Asia/Bangkok"))
        current_time = now.time()
        current_weekday = now.weekday()   # 0=Mon, 6=Sun

        if current_weekday not in rule.schedule_weekdays:
            return False

        time_from = time.fromisoformat(rule.schedule_from)  # "22:00"
        time_to   = time.fromisoformat(rule.schedule_to)    # "06:00"

        # Handle overnight schedule (22:00 → 06:00)
        if time_from > time_to:
            return current_time >= time_from or current_time < time_to
        else:
            return time_from <= current_time < time_to
```

---

## 4. System Boot State Machine

```
         [python main.py]
                │
                ▼
    ┌───────────────────────┐
    │    INITIALIZING        │
    │  load Settings(.env)  │
    │  validate config      │
    └──────────┬────────────┘
               │ error → EXIT(1) + log
               ▼
    ┌───────────────────────┐
    │   STARTING_SERVICES   │
    │  MessageBus.start()   │
    │  ConfigService.init() │
    │  StateRegistry.init() │
    └──────────┬────────────┘
               │ error → DEGRADED
               ▼
    ┌───────────────────────┐
    │   STARTING_CAMERAS    │
    │  CameraManager        │
    │  .start_all()         │
    │  (parallel connect)   │
    └──────────┬────────────┘
               │ ≥1 camera OK → continue
               │ 0 cameras → DEGRADED (ยังรัน API ได้)
               ▼
    ┌───────────────────────┐
    │    STARTING_AI        │
    │  load OpenVINO model  │
    │  AIPipeline.start()   │
    └──────────┬────────────┘
               │ error → DEGRADED (กล้องยังทำงาน, AI ไม่ทำงาน)
               ▼
    ┌───────────────────────┐
    │    STARTING_API       │
    │  FastAPI app create   │
    │  uvicorn.serve()      │
    └──────────┬────────────┘
               │
               ▼
    ┌───────────────────────┐
    │        RUNNING        │◄────────────────────────────────────┐
    │  ทุก service ทำงาน   │                                     │
    │  HEALTH_BEAT every   │  (หาก service หนึ่งพัง → DEGRADED)  │
    │  10s                  │                                     │
    └──────────┬────────────┘                                     │
               │ SIGTERM / Ctrl+C                                 │
               ▼                                                   │
    ┌───────────────────────┐         ┌───────────────────────┐   │
    │   SHUTTING_DOWN       │         │      DEGRADED          │───┘
    │  graceful shutdown:   │         │  บาง service พัง      │
    │  - finish current     │         │  HEALTH_BEAT warning   │
    │    inference          │         │  API ยังตอบได้        │
    │  - flush DB writes    │         │  auto-recover attempt  │
    │  - close cameras      │         └───────────────────────┘
    │  - close DB           │
    └──────────┬────────────┘
               │
               ▼
           EXIT(0)
```

### Boot Failure Handling

```python
# main.py
async def main():
    system_status = "initializing"
    try:
        cfg = Settings()                          # EXIT if .env invalid
        bus = await start_message_bus()
        config_svc = await start_config_service(bus)
        cameras_ok = await start_cameras(config_svc, bus)  # partial OK allowed
        ai_ok      = await start_ai_pipeline(bus)          # partial OK allowed
        app        = create_api(config_svc, bus)

        if not cameras_ok or not ai_ok:
            system_status = "degraded"            # ยังรันได้ แต่ warn
            logger.warning("System starting in DEGRADED mode")
        else:
            system_status = "running"

        await serve(app)

    except SettingsError as e:
        logger.critical("Cannot start: invalid config — %s", e)
        sys.exit(1)

    except Exception as e:
        logger.critical("Unexpected startup failure: %s", e)
        sys.exit(1)
```

---

## 5. Cross-OS Service Lifecycle

### Windows (NSSM หรือ Task Scheduler)

```
STOPPED ──[start]──► RUNNING ──[stop]──► STOPPING ──► STOPPED
                         │
                    [crash/error]
                         │
                         ▼
                  AUTO-RESTART (NSSM)
                  delay: 5 seconds
```

```powershell
# ติดตั้ง NSSM (Non-Sucking Service Manager)
# https://nssm.cc/

nssm install MTSecurity "D:\dev\MTSecurity\my_env\Scripts\python.exe"
nssm set MTSecurity AppParameters "D:\dev\MTSecurity\my_workspace\backend\main.py"
nssm set MTSecurity AppDirectory "D:\dev\MTSecurity\my_workspace\backend"
nssm set MTSecurity AppRestartDelay 5000
nssm start MTSecurity
```

### Linux (systemd)

```ini
# /etc/systemd/system/mtsecurity.service
[Unit]
Description=MTSecurity AI Camera System
After=network.target

[Service]
Type=simple
User=mtsecurity
WorkingDirectory=/opt/mtsecurity/backend
ExecStart=/opt/mtsecurity/venv/bin/python main.py
Restart=on-failure
RestartSec=5s
EnvironmentFile=/opt/mtsecurity/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable mtsecurity
sudo systemctl start mtsecurity
sudo systemctl status mtsecurity
```

### macOS (launchd)

```xml
<!-- ~/Library/LaunchAgents/com.mtsecurity.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>com.mtsecurity</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/user/mtsecurity/venv/bin/python</string>
        <string>/Users/user/mtsecurity/backend/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/user/mtsecurity/backend</string>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
</dict>
</plist>
```

```bash
launchctl load ~/Library/LaunchAgents/com.mtsecurity.plist
launchctl start com.mtsecurity
```
