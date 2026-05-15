# MTSecurity v2 — Frontend Architecture Map

> Generated: 2026-05-15 | Claude Sonnet 4.6
> Stack: Vue 3 + Pinia + Vue Router + TypeScript + Vite + DaisyUI v5 + Tailwind CSS v4

---

## 1. Directory Tree

```
frontend/
├── index.html                       # SPA root — mounts #app
├── vite.config.ts                   # Vite dev server + proxy to backend
├── tailwind.config.ts               # Tailwind (minimal — v4 uses CSS-first)
├── package.json
│
└── src/
    ├── main.ts                      # App bootstrap — createApp, Pinia, Router, mount
    ├── App.vue                      # Root component — <RouterView> only
    ├── env.d.ts                     # Vite env type declarations
    ├── style.css                    # Global CSS — Tailwind + glow/glass utilities
    │
    ├── api/
    │   └── client.ts                # All API calls + TypeScript types
    │
    ├── router/
    │   └── index.ts                 # Route definitions + auth guard
    │
    ├── stores/                      # Pinia stores (global reactive state)
    │   ├── auth.ts                  # Auth state, login/logout, /me
    │   ├── cameras.ts               # Camera list, statuses, patchStatus (WS updates)
    │   ├── events.ts                # Alert queue, newCount, ack/silence/escalate
    │   ├── zones.ts                 # Zones + rules lists
    │   ├── system.ts                # Health polling + WebSocket lifecycle
    │   ├── theme.ts                 # DaisyUI theme selection + localStorage
    │   └── toast.ts                 # Toast notification queue
    │
    ├── composables/
    │   ├── useUiHelpers.ts          # Shared formatting/color helpers (gaugeColor, sevBadgeClass, etc.)
    │   └── useServerTable.ts        # (created but not actively used — see notes)
    │
    ├── components/
    │   ├── AppLayout.vue            # Shell: sidebar + topbar + status bar + toast
    │   ├── ZoneCanvas.vue           # SVG polygon drawing on camera frame
    │   ├── RuleLogicBuilder.vue     # AND/OR/NOT logic tree UI for rules
    │   ├── SchedulePicker.vue       # Time-window schedule editor for rules
    │   └── HelloWorld.vue           # (unused, Vite scaffold leftover)
    │
    └── views/
        ├── LoginView.vue            # Auth form (glassmorphism card)
        ├── DashboardView.vue        # Stats overview + recent alerts table
        ├── PilotView.vue            # Operator cockpit (live video + alert queue)
        ├── CamerasView.vue          # Camera management (list + cards + add)
        ├── EventsView.vue           # Paginated alert log with server-side filters
        ├── ZonesView.vue            # Zone drawing + rule management per camera
        └── SettingsView.vue         # System health, theme, account info
```

---

## 2. Bootstrap Sequence (main.ts → App.vue)

```
Browser loads index.html
    │
    ├─ src/main.ts
    │    ├─ createApp(App)
    │    ├─ app.use(createPinia())        ← Pinia before Router (stores may be used in guards)
    │    ├─ app.use(router)
    │    └─ app.mount('#app')
    │
    ├─ src/App.vue
    │    ├─ useThemeStore()              ← ensures theme is tracked by Pinia from first render
    │    └─ <RouterView />              ← renders current route component
    │
    ├─ src/router/index.ts
    │    └─ router.beforeEach()         ← auth guard (checks localStorage access_token)
    │         ├─ requiresAuth + no token → redirect /login
    │         └─ on /login + token → redirect /dashboard
    │
    └─ Route component mounts
         └─ onMounted() → store.fetchAll() / system.init() etc.
```

**Default route:** `/` redirects to `/pilot`

---

## 3. Routes

| Path | Name | Component | Auth? | Notes |
|------|------|-----------|-------|-------|
| `/` | — | (redirect) | — | → `/pilot` |
| `/login` | login | LoginView | Public | Redirect to /dashboard if already authed |
| `/pilot` | pilot | PilotView | ✅ | Default landing — operator cockpit |
| `/dashboard` | dashboard | DashboardView | ✅ | Overview stats |
| `/cameras` | cameras | CamerasView | ✅ | Camera management |
| `/events` | events | EventsView | ✅ | Alert log (paginated + filtered) |
| `/zones` | zones | ZonesView | ✅ | Zone + rule editor |
| `/settings` | settings | SettingsView | ✅ | System info + theme + account |

**Auth guard:** reads `localStorage.getItem('access_token')` — token presence only (no JWT decode).
> ⚠️ Known limitation: expired token is not detected client-side until the first API call returns 401 (which then clears token and redirects to /login via `client.ts`).

---

## 4. API Client (api/client.ts)

Single file — all API calls and TypeScript types.

### Base URL
```typescript
const BASE = '/api/v1'  // relative — proxied by Vite in dev, nginx in prod
```

### Auth Header
```typescript
// Every request automatically adds:
Authorization: Bearer <localStorage.access_token>

// 401 response:
→ clears access_token + refresh_token from localStorage
→ window.location.href = '/login'
```

### API Namespaces

```typescript
authApi = {
  login(username, password)    → TokenResponse
  logout()                     → void
  refresh(refresh_token)       → TokenResponse
  me()                         → UserRead
}

camerasApi = {
  list()                       → CameraRead[]
  get(id)                      → CameraRead
  create(body)                 → CameraRead
  update(id, body)             → CameraRead
  delete(id)                   → void
  status(id)                   → CameraStatus
  listWebcams()                → WebcamDevice[]
}

eventsApi = {
  list(params?)                → EventRead[]   // params: page, page_size, severity, status, behavior, camera_id
  get(id)                      → EventRead
  acknowledge(id, note?)       → void
  silence(id, duration_seconds)→ void
  escalate(id, reason)         → void
}

zonesApi = {
  list()                       → ZoneRead[]
  get(id)                      → ZoneRead
  create(body)                 → ZoneRead
  delete(id)                   → void
}

rulesApi = {
  list()                       → RuleRead[]
  get(id)                      → RuleRead
  create(body)                 → RuleRead
  update(id, body)             → RuleRead
}

lprApi = {
  list()                       → LPRRead[]
  create(body)                 → LPRRead
  delete(id)                   → void
}

healthApi = {
  get()                        → HealthResponse
}
```

### Key TypeScript Types

```typescript
interface EventRead {
  id, camera_id, rule_id, behavior, severity, confidence, track_id,
  snapshot_url, clip_url, occurred_at, status, acknowledged_at, acknowledged_by
}

interface CameraStatus {
  camera_id, state, fps, latency_ms, last_frame_at, error_msg,
  tracks: any[] | null   // populated by WebSocket track_update messages
}

interface HealthResponse {
  status, version, uptime_seconds, boot_state,
  cameras: { total, online },
  system: { cpu_percent, ram_percent, platform }
}
```

---

## 5. Pinia Stores

### Store Dependency Map

```
AppLayout.vue
  ├── useAuthStore     (username, role, logout)
  ├── useSystemStore   (wsState, cpuPercent, ramPercent, init/destroy)
  └── useEventsStore   (newCount — for navbar bell badge)

PilotView.vue
  ├── useCamerasStore  (cameras[], statusOf, patchStatus)
  ├── useEventsStore   (events[], ack, ackAll)
  ├── useSystemStore   (cpuPercent, ramPercent, uptime, subscribeCamera)
  ├── useAuthStore     (token — for MJPEG stream URL)
  └── useZonesStore    (zones — for SVG overlay)

DashboardView.vue
  ├── useCamerasStore  (total, online, failed)
  ├── useEventsStore   (recentAlerts, newCount)
  └── useSystemStore   (cpuPercent, ramPercent, uptime, camerasOnline)

CamerasView.vue
  ├── useCamerasStore  (cameras, statuses, addCamera, setActive, listWebcams)
  └── useAuthStore     (token — for stream URL)

EventsView.vue           ← uses LOCAL state, NOT events store for rows
  ├── useEventsStore   (acknowledge/silence/escalate — to sync bell count)
  └── useAuthStore     (token — for snapshot URL)

ZonesView.vue
  └── useZonesStore    (zones, rules, fetchAll)
      + useCamerasStore (cameras list for tab selector)

SettingsView.vue
  ├── useAuthStore     (username, role, logout)
  ├── useSystemStore   (health, cpuPercent, ramPercent)
  └── useThemeStore    (currentTheme, setTheme)
```

---

### useAuthStore

```typescript
// State
user: UserRead | null         // full user object from /auth/me
token: string | null          // access_token (also in localStorage)

// Computed
isAuthenticated: boolean
username: string
role: string                  // "SUPERADMIN" | "ADMIN" | "OPERATOR" | "AUDITOR" | "VIEWER"
userInitial: string           // first letter of username, uppercase

// Actions
login(username, password)     // → POST /auth/login → stores tokens → fetchMe()
logout()                      // → POST /auth/logout → clears state + localStorage + cameras.reset()
fetchMe()                     // → GET /auth/me → populates user ref
```

---

### useCamerasStore

```typescript
// State
cameras: CameraRead[]         // all cameras from DB
statuses: Record<number, CameraStatus>  // keyed by camera_id

// Computed
total: number
online: number                // statuses with state === 'ONLINE'
reconnecting: number
failed: number                // ERROR or FAILED

// Actions
fetchAll()                    // GET /cameras + GET /cameras/{id}/status for each (parallel)
patchStatus(id, patch)        // merge partial CameraStatus (called by WebSocket handler)
statusOf(id) → CameraStatus | null
addCamera(body) → CameraRead  // POST /cameras
listWebcams() → WebcamDevice[]
setActive(id, isActive)       // PATCH /cameras/{id} {is_active}
reset()                       // clear all (called on logout — stops MJPEG streams)
```

**Key pattern:** `patchStatus()` is the bridge between WebSocket real-time data and the camera status display. Called from `useSystemStore.handleWsMessage()`.

---

### useEventsStore

```typescript
// State
events: EventRead[]           // up to 200 most recent events (live queue)
loading: boolean
error: string | null
latestAlert: EventRead | null // most recently arrived alert

// Computed
newCount: number              // events with status === 'NEW' (drives navbar bell)
recentAlerts: EventRead[]     // first 10

// Actions
fetchRecent(params?)          // GET /events?page_size=50 (default) — for shared queue
prependAlert(event)           // called by WS handler — adds to front, cap at 200
acknowledge(id, note?)        // POST /events/{id}/acknowledge → mutate local status
ackAll()                      // acknowledge all NEW events
silence(id, duration_seconds) // POST /events/{id}/silence → mutate local status
escalate(id, reason)          // POST /events/{id}/escalate → mutate local status
```

> **IMPORTANT:** `EventsView.vue` does NOT use `events.events` for its table.
> It uses a **local `rows` ref** and calls `eventsApi.list()` directly to avoid race conditions.
> The store's `events` array is only for the **global alert queue** (PilotView, navbar bell, DashboardView).
> See lessons_learned.md BUG-002.

---

### useSystemStore

```typescript
// State (reactive)
health: HealthResponse | null  // from GET /health
wsState: 'disconnected' | 'connecting' | 'connected' | 'error'
lastHealthAt: Date | null

// Computed
isOnline: boolean
cpuPercent, ramPercent, camerasOnline, camerasTotal, uptime

// Actions
fetchHealth()                  // GET /health → updates health ref
startPolling(intervalMs=10000) // fetch health every 10s
stopPolling()
connectWs()                    // open WebSocket at /api/v1/ws?token=...
                               // auto-reconnect after 5s on close
disconnectWs()
subscribeCamera(ids[])         // send {"type":"subscribe","camera_ids":[...]}
init()                         // startPolling() + connectWs()
destroy()                      // stopPolling() + disconnectWs()

// WebSocket message routing (handleWsMessage)
"alert_fired"    → eventsStore.prependAlert(msg.data)
"frame_ready"    → camerasStore.patchStatus(id, {fps, state:'ONLINE', last_frame_at})
"track_update"   → camerasStore.patchStatus(id, {tracks: msg.data.detections})
```

**Lifecycle:** `init()` called in `AppLayout.vue` onMounted, `destroy()` called onUnmounted.

---

### useZonesStore

```typescript
// State
zones: ZoneRead[]    // all zones (all cameras)
rules: RuleRead[]    // all rules (all zones)
loading: boolean

// Actions
fetchAll()           // parallel: GET /zones + GET /rules
zonesForCamera(cameraId) → ZoneRead[]
rulesForZone(zoneId)     → RuleRead[]
```

---

### useThemeStore

```typescript
// Applied IMMEDIATELY at module load (before Vue mounts) to prevent flash
const _saved = localStorage.getItem('mt-theme') ?? 'dark'
document.documentElement.setAttribute('data-theme', _saved)

// State
currentTheme: string

// Actions
setTheme(theme)    // setAttribute on <html> + localStorage.setItem
```

---

### useToastStore

```typescript
// State
toasts: Toast[]    // { id, type, message, title? }

// Actions
push(toast, durationMs=5000)  // add toast, auto-remove after duration
remove(id)
```

**Note:** Toast store is defined but no component currently renders it. Needs a `<ToastContainer>` in AppLayout to be visible.

---

## 6. Components

### AppLayout.vue — Main Shell

```
┌─────────────────────────────────────────────────────┐
│  SIDEBAR (w-60, fixed)                               │
│  ┌──────────────────────────────────────────────┐   │
│  │ [Logo + glow orb]  MT Security  v2.0.0      │   │
│  │ ── NAVIGATION ──────────────────────────    │   │
│  │  ● Pilot Console    (active: gradient+border) │   │
│  │    Dashboard                                  │   │
│  │    Cameras                                    │   │
│  │    Events                                     │   │
│  │    Zones                                      │   │
│  │    Settings                                   │   │
│  │ ── SYSTEM HEALTH ───────────────────────     │   │
│  │  CPU  ████░░  34%                            │   │
│  │  RAM  ██████  61%                            │   │
│  │  ● WS LIVE                                   │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  TOP NAVBAR (h-14, fixed, ml-60)                     │
│  [ Page icon + "PILOT CONSOLE" ]  [WS●] [🔔3] [☀] [▼] │
│                                                      │
│  MAIN CONTENT AREA (ml-60, pt-14)                    │
│  ┌──────────────────────────────────────────────┐   │
│  │ <slot /> (view content)                      │   │
│  └──────────────────────────────────────────────┘   │
│                                                      │
│  STATUS BAR (fixed bottom)                           │
│  [● ONLINE] [🔔 3 ALERTS] [↑ 03:42:11] [📷 4/5 CAM] │
└─────────────────────────────────────────────────────┘
```

**Key responsibilities:**
- Renders sidebar nav, top navbar, status bar
- Calls `system.init()` on mount, `system.destroy()` on unmount
- Calls `events.fetchRecent()` on mount (for navbar bell count)
- Calls `auth.fetchMe()` on mount (populate user display)
- Provides `<slot>` and named `#header` slot for view content

**Active nav detection:**
```typescript
const route = useRoute()
function isActive(path: string) { return route.path === path }
// Class: nav-active-gradient + text-primary for active, ghost for inactive
```

---

### ZoneCanvas.vue — SVG Zone Drawing

**Purpose:** Allows operator to draw a polygon zone on top of a live camera frame.

```
Props:
  camera-id: number
  camera-name: string
  stream-url: string

Emits:
  cancel()
  save(zone: { name, coordinates, color })

Internal:
  points: [x,y][]        // normalized 0.0–1.0 coordinates
  drawing: boolean
  svgEl: SVGElement ref  // for click coordinate calculation

Key logic:
  @click on SVG → normalize click coords relative to image dims
  First point closes polygon if clicked within 15px radius
  Output coordinates: [[x1,y1],[x2,y2],...] (normalized)
```

---

### RuleLogicBuilder.vue — AND/OR/NOT Tree UI

**Purpose:** Visual editor for advanced rule conditions (LogicNode trees).

```
Props:
  modelValue: LogicNode  // {type: "AND"|"OR"|"NOT", conditions: [...]}
  depth: number (default 0)

Emits:
  update:modelValue

Structure:
  Recursive component — each node renders its children
  Leaf types: time_window, space_zone, object_class, behavior_match
  Operators: AND, OR, NOT
```

---

### SchedulePicker.vue — Time Window Editor

**Purpose:** Edit rule schedule (which days and times the rule is active).

```
Props:
  modelValue: Schedule  // {enabled, windows: [{days: [1..7], start: "HH:MM", end: "HH:MM"}]}

Emits:
  update:modelValue

UI: day checkboxes (Mon–Sun) + time inputs per window
```

---

## 7. Views

### LoginView.vue

```
State: username, password, loading, error

Template:
  Full-screen bg (animated gradient + dot grid)
  Glass card (backdrop-blur, border-t-4 border-primary, glow-primary)
    Logo with shadow glow
    Input fields (username, password)
    Submit button (gradient, loading spinner)
    Error alert
  "SECURE CONNECTION" pulsing indicator below card

onMounted: no data fetch
Submit: auth.login() → router.push('/dashboard') on success
```

---

### DashboardView.vue

```
Data sources: camerasStore, eventsStore, systemStore

onMounted:
  cameras.fetchAll()
  events.fetchRecent()
  system.fetchHealth()

Template sections:
  1. STAT CARDS (4 across)
     - Active Cameras (online/total, error glow if any failed)
     - New Alerts (newCount, error glow if > 0)
     - CPU % (progress bar, glow at ≥70%)
     - System Uptime
  2. SPLIT LAYOUT
     Left: RECENT ALERTS table
       - Columns: TIME | CAM | TYPE | SEV | STATUS | ACK action
       - Severity strip on left of each row
       - Inline ACK button for NEW events
     Right: CAMERA STATUS panel
       - List of cameras with status dot + state badge
       - ONLINE cameras get glow-success border
       - Link to open in Pilot
```

---

### PilotView.vue — Operator Cockpit ⭐ Most Complex View

```
Layout: 2-column (flex-row on lg+)
  Left (flex-[2]):
    1. Primary Video Feed (flex-1, occupies most height)
       - <img :src="streamUrl(primaryCamera.id)" />  ← MJPEG stream
       - SVG overlay (absolute, z-30):
           Zone polygons (filled, colored, dashed outline)
           AI bounding boxes (rect + centroid dot + label HUD)
       - HUD top-left: LIVE badge + resolution/FPS
       - HUD top-right: Layer toggles (AI/Zones/HUD) + Fullscreen button
    2. Camera Thumbnail Strip (h-44, overflow-x-auto)
       - Card per camera: stream thumbnail + alert glow ring + footer label + status dot
       - Click → setPrimary(cam.id)

  Right (w-400px):
    3. Alert Queue
       Header: ping dot + "ALERT QUEUE" + count + [FILTERS] [ACK ALL]
       Filter bar (expandable): severity select + UNACKED toggle
       Alert list (scrollable):
         Each alert: left color strip | severity badge | behavior | CAM badge | confidence + time | hover actions (VIEW / ACK)
         Empty state: green checkmark glow + "ALL CLEAR"
    4. System Telemetry (DaisyUI stats)
       3 stats: CPU (%) | RAM (%) | CAMERAS (online/total)
       Each with progress bar
       Uptime row
       Keyboard shortcut legend (kbd elements)

Keyboard shortcuts (handleKeydown):
  1-9      → switch to camera by index
  0        → camera 10
  Space    → ACK latest NEW alert
  F        → fullscreen primary feed
  Esc      → close modal

Modal (Evidence Snapshot):
  Triggered by: new high/critical alert (watcher on events[0])
  Content: event snapshot image + metadata + note textarea + RESOLVE button
  <dialog id="alert_modal"> (DaisyUI modal)

onMounted:
  cameras.fetchAll()
  events.fetchRecent()
  zones.fetchAll()
  setPrimary(cameras[0].id)  → system.subscribeCamera([id])
  setInterval(() => now.value = Date.now(), 500)  ← drives hasRecentAlert() flash

Key computed:
  primaryCamera  → cameras.cameras.find(c => c.id === primaryId)
  activeZones    → zones filtered by primaryId
  activeTracks   → cameras.statusOf(primaryId)?.tracks  ← from WS track_update
  filteredAlerts → events.events filtered by severity + unackedOnly
  currentFps     → cameras.statusOf(primaryId)?.fps
```

---

### CamerasView.vue

```
Tabs: CARD VIEW | LIST VIEW

Data: camerasStore.cameras[], statuses
onMounted: cameras.fetchAll()

Card View:
  Grid of camera cards (md:grid-cols-2 lg:grid-cols-3)
  Each card:
    - MJPEG stream <img> (aspect-video, object-cover)
    - Status dot + badge overlay
    - Footer: name + location + fps + resolution
    - Hover overlay: action buttons (Pilot link, Toggle active, Delete, Error info)
    - Alert glow ring (glow-error) if has NEW alert for this camera

List View (table):
  Columns: NAME | SOURCE | LOCATION | RESOLUTION | FPS | STATUS | ACTIONS
  Action buttons: Error tooltip | View in Pilot (RouterLink) | Open stream (external link)
  table-pin-rows → sticky header

Add Camera modal (DaisyUI dialog):
  Step 1: source_type select (RTSP | Webcam)
  RTSP: rtsp_url input + name + location + fps
  Webcam: device_index select (populated from listWebcams()) + name + location
  POST /cameras on submit
```

---

### EventsView.vue — Server-side Paginated Alert Log

```
⚠️ Uses LOCAL state (NOT shared events store) to avoid race conditions

Local state:
  rows: EventRead[]     // local, written by eventsApi.list() only
  loading: boolean
  page: number          // starts at 1
  pageSize: number      // default 25
  hasNextPage: boolean  // rows.length >= pageSize
  severity: string      // '' | 'critical' | 'high' | 'medium' | 'low'
  status: string        // '' | 'NEW' | 'ACKNOWLEDGED' | 'SILENCED' | 'ESCALATED'
  behavior: string      // '' | 'intrusion' | 'loitering' | ...

onMounted: load()

load():
  params = { page, page_size: pageSize }
  if severity → params.severity = severity
  if status   → params.status = status
  if behavior → params.behavior = behavior
  rows.value = await eventsApi.list(params)
  hasNextPage = rows.length >= pageSize

Page size control:
  Button group [10][25][50][100]
  @click → onPageSizeClick(s) → pageSize = s, page = 1, load()

Filter controls:
  v-model + @change="resetAndLoad" on each <select>
  resetAndLoad() → page = 1, load()

Pagination:
  PREV/NEXT buttons → prevPage() / nextPage() → load()

Table (table-pin-rows):
  Cols: [strip] | TIME | CAM | TYPE | SEV | CONF | STATUS | ACTIONS
  Left severity strip (w-1 colored bar)
  ACTIONS: snapshot (external link) | ACK ✓ | SILENCE 🔇 | ESCALATE ▲

Bulk action bar:
  Shows if newCount > 0: "N UNACKNOWLEDGED ALERTS" + [ACK ALL] button
  backdrop-blur-sm + glow-error

Action flow (ack/silence/escalate):
  1. Call eventsApi.*(id)
  2. Mutate ev.status in local rows
  3. Call eventsStore.*(id)  ← keeps navbar bell count accurate
```

---

### ZonesView.vue

```
Data: zonesStore.zones, zonesStore.rules, camerasStore.cameras
onMounted: cameras.fetchAll(), zones.fetchAll()

Camera selector: tabs-boxed (one tab per camera)

Zone list (per selected camera):
  Each zone card:
    Left border = zone.color (inline style)
    Header: zone name + active badge + point count + delete button
    Rule list (per zone):
      Each rule row: severity badge | name | behavior + thresholds | hover actions (edit/toggle/delete)
      ADD RULE button (dashed border)

Add/Edit Rule Modal (DaisyUI dialog):
  Basic fields: name, severity, behavior, confidence_threshold, dwell, cooldown
  Advanced: toggle for "Advanced Logic" (shows RuleLogicBuilder)
  Schedule: toggle for custom schedule (shows SchedulePicker)
  POST /rules on create, PATCH /rules/{id} on edit

Zone Drawing: opens ZoneCanvas.vue
  After save: POST /zones, reload zones
```

---

### SettingsView.vue

```
Tabs: SYSTEM | DISPLAY | ACCOUNT

SYSTEM tab:
  System Status card (grid 3 cols):
    VERSION | UPTIME | PLATFORM
    CPU (progress bar + %) | RAM (progress bar + %) | BOOT STATE
    CAMERAS (online/total) | WEBSOCKET (state) | LAST POLL
    [REFRESH] button → system.fetchHealth()
  Notification Channels card:
    List: LINE / Discord / Slack / Email / MQTT / Webhook
    Each: icon + name + desc + CONFIGURED/NOT SET badge
    (configured value is static false — TODO: read from backend)

DISPLAY tab:
  Theme grid (2-4 cols):
    Button per theme: color swatch dots + name
    Active: btn-primary + green indicator dot
  Preview row: semantic color badges

ACCOUNT tab:
  Avatar circle (w-14 h-14, role-colored):
    SUPERADMIN → bg-error  |  ADMIN → bg-warning
    OPERATOR → bg-primary  |  VIEWER → bg-neutral
  Username + role badge
  Session grid: USERNAME | ROLE | STATUS
  [SIGN OUT] button → auth.logout() → router.push('/login')
```

---

## 8. Global CSS (style.css)

```css
/* Utility classes added for the security ops aesthetic */

.glow-success { box-shadow: 0 0 12px oklch(var(--su)/0.4); }
.glow-error   { box-shadow: 0 0 12px oklch(var(--er)/0.5); }
.glow-warning { box-shadow: 0 0 12px oklch(var(--wa)/0.3); }
.glow-primary { box-shadow: 0 0 16px oklch(var(--p)/0.35); }

.glass-card {
  background: oklch(var(--b1)/0.85);
  backdrop-filter: blur(12px);
  border: 1px solid oklch(var(--bc)/0.08);
}

.nav-active-gradient {
  background: linear-gradient(90deg, oklch(var(--p)/0.15) 0%, transparent 100%);
  border-left: 2px solid oklch(var(--p));
}

@keyframes status-ping { /* pulsing status dots */ }
.status-ping { animation: status-ping 2s ease-in-out infinite; }

.scrollbar-hide { scrollbar-width: none; }
```

---

## 9. Composables

### useUiHelpers.ts — Shared Formatting (pure functions, no state)

```typescript
gaugeColor(pct: number) → string      // 'text-error' | 'text-warning' | 'text-success'
progressColor(pct: number) → string   // 'progress-error' | 'progress-warning' | 'progress-success'
sevBadgeClass(severity: string) → string  // 'badge-error' | 'badge-warning' | 'badge-info' | 'badge-ghost'
statusBadgeClass(status: string) → string // 'badge-error' | 'badge-success' | 'badge-ghost' | 'badge-warning'
camDotClass(state?: string) → string  // 'bg-success animate-pulse' | ... (for status dots)
camBadgeClass(state?: string) → string // 'badge-success' | ... (for state labels)
fmtTime(iso: string) → string         // "14:23:01"
fmtDateTime(iso: string) → string     // "05/15 14:23:01"
fmtBehavior(behavior: string) → string // "intrusion_detection" → "intrusion detection"
```

> **Note:** Not all views import from useUiHelpers — some views (PilotView, EventsView) have their own local copies of these functions. If adding similar functions, prefer centralizing in useUiHelpers.

### useServerTable.ts — (Deprecated / Unused)

Created during EventsView development as a composable for server-side pagination. Superseded by simpler local refs in EventsView. File exists on disk but is not imported anywhere. Safe to delete or repurpose.

---

## 10. Vite Config (vite.config.ts)

```typescript
server: {
  port: 5173,
  proxy: {
    '/api': {
      target: env.VITE_BACKEND_URL || 'http://localhost:8000',
      changeOrigin: true,
      ws: true,   // WebSocket upgrade for /api/v1/ws
    },
  },
}
```

**Effect:** All requests to `/api/*` are proxied to backend. Frontend never hardcodes backend URL.

**MJPEG stream:** `/api/v1/cameras/{id}/stream?token=<JWT>` — served as `StreamingResponse` from backend, displayed in `<img>` tag. Browser natively handles multipart/x-mixed-replace.

---

## 11. WebSocket Message Flow (Frontend)

```
Backend WebSocket (/api/v1/ws)
         │
         │ (JSON frames)
         ▼
useSystemStore.handleWsMessage(msg)
  │
  ├─ type: "alert_fired"
  │    → eventsStore.prependAlert(msg.data)
  │    → PilotView watcher triggers: if high/critical → openModal()
  │    → AppLayout: newCount badge updates reactively
  │
  ├─ type: "frame_ready"
  │    → camerasStore.patchStatus(cam_id, { fps, state:'ONLINE', last_frame_at })
  │    → DashboardView: camera status dots update
  │    → CamerasView: status badges update
  │
  └─ type: "track_update"
       → camerasStore.patchStatus(cam_id, { tracks: detections[] })
       → PilotView: activeTracks computed updates
       → SVG bounding boxes re-render in real-time

Auto-reconnect:
  ws.onclose → setTimeout(connectWs, 5000)   ← reconnects after 5s
```

---

## 12. Key Patterns & Conventions

### DaisyUI Component Usage

| Element | DaisyUI class | Notes |
|---------|--------------|-------|
| Cards | `card bg-base-100 border border-base-300` | No `shadow-none` needed — default has shadow |
| Tables | `table table-sm table-pin-rows` | `table-pin-rows` = sticky header |
| Buttons | `btn btn-xs btn-ghost` | xs for action icons, sm for toolbar |
| Badges | `badge badge-xs badge-error font-mono` | font-mono for all status badges |
| Selects | `select select-xs select-bordered font-mono` | filter dropdowns |
| Stats | `stats stats-horizontal` | system telemetry panels |
| Modals | `<dialog>` + `.showModal()` / `.close()` | Use native dialog for backdrop |
| Join | `join` + `join-item` | Button groups (page sizes) |
| Loading | `loading loading-spinner loading-xs` | Inline loading indicator |

### Tailwind Patterns

```
Font conventions:
  font-mono       ← all telemetry data, IDs, codes, times
  tracking-widest ← section labels (UPPERCASE)
  text-xs         ← most UI text
  text-[9px]      ← smallest labels (tracking info, tooltips)

Opacity conventions:
  opacity-40      ← section labels / secondary text
  opacity-60      ← muted data
  opacity-100     ← active / hover state

Glow classes (custom):
  glow-success    ← online cameras, ACK buttons
  glow-error      ← alert cards, unread count
  glow-primary    ← logo, primary accents
```

### Color Semantics (DO NOT violate)
```
error   = alert / critical / offline
warning = high severity / reconnecting / caution
success = online / acknowledged / safe
info    = medium severity / neutral status
primary = selected / active / focus
ghost   = low severity / inactive / muted
```

---

## 13. State Ownership Rules

```
Global (Pinia store):
  auth:    user identity, token — app-wide
  cameras: camera list, statuses — updated by WS + API
  events:  live alert queue (up to 200) — updated by WS (prependAlert)
  system:  health + WS lifecycle — polled every 10s
  zones:   zone/rule configs — loaded on demand by ZonesView + PilotView
  theme:   DaisyUI theme selection

Local (ref in view):
  EventsView.rows    ← paginated/filtered — NOT shared (race condition risk)
  PilotView.primaryId ← which camera is focused
  ZonesView.selectedCamId ← which camera tab is active
  Any form state     ← always local

Rule: If two components need the same data concurrently, use Pinia.
      If only one view needs it with pagination/filtering, use local ref + direct API call.
```

---

## 14. Files to Check When Debugging Frontend Issues

| Symptom | File to Check | What to Look For |
|---------|--------------|------------------|
| Login fails | `stores/auth.ts` + `api/client.ts` | Token storage, 401 handling |
| Data not loading on mount | View's `onMounted()` | Missing await, wrong store action |
| Filter/pagination not working | `views/EventsView.vue` + `api/client.ts` | params object, URLSearchParams |
| Real-time updates not showing | `stores/system.ts` handleWsMessage | msg.type match, patchStatus call |
| Camera stream not showing | `views/PilotView.vue` streamUrl() | token in URL, backend MJPEG |
| SVG overlay wrong position | `views/PilotView.vue` scaleCoords() | vWidth/vHeight, onImageLoad |
| Theme flash on load | `stores/theme.ts` | Module-level applyTheme() call |
| Bell count wrong | `stores/events.ts` newCount | filter condition |
| WS disconnected after idle | `stores/system.ts` connectWs() | reconnect timer logic |
| Race condition overwrites data | See lessons_learned.md BUG-002 | local ref vs shared store |
