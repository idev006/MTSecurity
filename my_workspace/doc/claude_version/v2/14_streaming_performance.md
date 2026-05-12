# 14 — Streaming Performance Design
### 10 Cameras Without Lag · Resolution Tiers · Canvas Overlay · WebSocket Protocol

---

## 1. Core Challenge

```
ต้องการ: ดูกล้อง 10 ตัวพร้อมกัน ไม่ lag + AI overlay
Hardware: CPU-only, Ryzen, 16GB RAM, LAN 100Mbps

ปัญหาหลัก:
  10 กล้อง × 30 FPS × 1080p = ~300 Mbps ← เกิน bandwidth
  10 กล้อง × 30 FPS × AI inference = CPU ตาย

วิธีแก้: Resolution Tier System + Smart Streaming
```

---

## 2. Resolution Tier System

```
┌─────────────────────────────────────────────────────────────────┐
│                    RESOLUTION TIERS                              │
├──────────────┬────────────┬────────────┬────────────────────────┤
│ Tier         │ Resolution │ FPS        │ ใช้สำหรับ              │
├──────────────┼────────────┼────────────┼────────────────────────┤
│ THUMBNAIL    │ 320 × 180  │ 3 FPS      │ Grid 10 กล้อง          │
│ MONITOR      │ 640 × 360  │ 10 FPS     │ Primary feed (เลือก)  │
│ DETAIL       │ 1280 × 720 │ 15 FPS     │ Fullscreen mode        │
│ EVIDENCE     │ ต้นฉบับ    │ เมื่อ event│ Snapshot + Clip        │
└──────────────┴────────────┴────────────┴────────────────────────┘
```

### Bandwidth ที่ใช้จริง

```
Grid (10 × THUMBNAIL, JPEG 65%)  :  10 × 320×180 × 3fps × 15KB  ≈  4.5 Mbps
Primary (1 × MONITOR, JPEG 75%)  :   1 × 640×360 × 10fps × 35KB ≈  2.8 Mbps
─────────────────────────────────────────────────────────────────────────────
รวม                               :  ≈ 7.3 Mbps  ✅ ต่ำกว่า 100Mbps มาก
```

### CPU Budget สำหรับ Encoding

```
JPEG encode 320×180 × 3fps × 10 กล้อง  :  ~8% CPU
JPEG encode 640×360 × 10fps × 1 กล้อง  :  ~5% CPU
AI inference (motion-triggered)          :  ~40% CPU
Motion detection × 10                   :  ~10% CPU
FastAPI + overhead                       :  ~5% CPU
───────────────────────────────────────────────────
รวม                                      :  ~68% CPU  ✅ มี headroom 32%
```

---

## 3. Backend Streaming Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    STREAM MANAGER                                  │
│                                                                    │
│  CameraThread × 10                                                 │
│  ┌──────────┐  ┌──────────┐  ...  ┌──────────┐                   │
│  │ CAM-01   │  │ CAM-02   │       │ CAM-10   │                    │
│  │ capture  │  │ capture  │       │ capture  │                    │
│  │ 10 FPS   │  │ 10 FPS   │       │ 10 FPS   │                    │
│  └────┬─────┘  └────┬─────┘       └────┬─────┘                   │
│       │              │                  │                          │
│       └──────────────┴──────────────────┘                         │
│                          │                                         │
│                          ▼                                         │
│              ┌───────────────────────┐                            │
│              │    FrameProcessor     │                            │
│              │  per camera_id:       │                            │
│              │  - resize → THUMBNAIL │  ← asyncio task           │
│              │  - resize → MONITOR   │    (non-blocking)         │
│              │  - draw overlay       │                            │
│              │  - JPEG encode        │                            │
│              └───────────┬───────────┘                            │
│                          │                                         │
│                          ▼                                         │
│              ┌───────────────────────┐                            │
│              │   StreamCache         │                            │
│              │  dict[cam_id] = {     │  ← in-memory               │
│              │    thumbnail: bytes,  │    TTL: 1s                 │
│              │    monitor: bytes,    │                            │
│              │    overlay_data: dict │                            │
│              │  }                   │                            │
│              └───────────┬───────────┘                            │
└──────────────────────────┼───────────────────────────────────────┘
                           │
                    WebSocket Hub
                    /ws/grid          ← ส่ง THUMBNAIL ทุก 333ms (3fps)
                    /ws/stream/{id}   ← ส่ง MONITOR ทุก 100ms (10fps)
```

### FrameProcessor Implementation

```python
# ingestion/frame_processor.py
import asyncio
import cv2
import numpy as np
from dataclasses import dataclass

THUMBNAIL_SIZE = (320, 180)
MONITOR_SIZE   = (640, 360)
JPEG_QUALITY_THUMB   = 65
JPEG_QUALITY_MONITOR = 75

@dataclass
class ProcessedFrame:
    camera_id:    int
    thumbnail:    bytes          # JPEG bytes
    monitor:      bytes          # JPEG bytes
    overlay_data: dict           # {tracks, zones, alerts} — ส่งแยก ไม่ burn-in
    timestamp:    float

class FrameProcessor:
    def __init__(self, stream_cache: "StreamCache"):
        self._cache = stream_cache

    async def process(self, camera_id: int, frame: np.ndarray,
                      overlay: dict) -> None:
        # Run in thread pool — cv2 ops เป็น blocking
        loop = asyncio.get_event_loop()
        processed = await loop.run_in_executor(
            None, self._process_sync, camera_id, frame, overlay
        )
        self._cache.update(camera_id, processed)

    def _process_sync(self, camera_id: int, frame: np.ndarray,
                      overlay: dict) -> ProcessedFrame:
        # Resize
        thumb   = cv2.resize(frame, THUMBNAIL_SIZE, interpolation=cv2.INTER_AREA)
        monitor = cv2.resize(frame, MONITOR_SIZE,   interpolation=cv2.INTER_LINEAR)

        # JPEG encode
        _, thumb_bytes   = cv2.imencode('.jpg', thumb,
                           [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY_THUMB])
        _, monitor_bytes = cv2.imencode('.jpg', monitor,
                           [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY_MONITOR])

        return ProcessedFrame(
            camera_id    = camera_id,
            thumbnail    = thumb_bytes.tobytes(),
            monitor      = monitor_bytes.tobytes(),
            overlay_data = overlay,   # bbox, zones, tracks — วาดที่ frontend
            timestamp    = time.time(),
        )
```

---

## 4. WebSocket Protocol (Frontend ↔ Backend)

### /ws/grid — ส่ง Thumbnail ทุกกล้องพร้อมกัน

```typescript
// Frontend Vue composable
// composables/useGridStream.ts

interface GridFrame {
  type:      "grid_update"
  frames: {
    [camera_id: number]: {
      jpeg_b64:  string        // base64 JPEG thumbnail
      overlay:   OverlayData   // วาดทับบน Canvas
      status:    "online" | "offline" | "alert"
      timestamp: number
    }
  }
}

// Backend ส่งทุก 333ms (3 FPS) — 1 message รวมทุกกล้อง
// ไม่ใช่ 10 messages แยกกัน → ลด overhead
```

### /ws/stream/{camera_id} — Primary Feed

```typescript
interface StreamFrame {
  type:      "stream_frame"
  camera_id: number
  jpeg_b64:  string          // base64 JPEG monitor resolution
  overlay:   OverlayData     // bbox + zones + tracks
  timestamp: number
}
```

### OverlayData Schema

```typescript
interface OverlayData {
  tracks: {
    track_id:    number
    class_name:  string         // "person" | "car" | "bag"
    confidence:  number
    bbox: {
      x1: number; y1: number    // normalized 0.0–1.0
      x2: number; y2: number
    }
    dwell_time:  number         // seconds
    is_loitering: boolean
  }[]
  zones: {
    zone_id:   number
    name:      string
    coords:    [number, number][] // normalized polygon
    color_hex: string
    is_alert:  boolean
  }[]
  alert_active: boolean
}
```

---

## 5. Frontend Canvas Overlay Rendering

### ทำไมต้องใช้ Canvas ไม่ใช่ DOM

```
DOM elements (div, svg):
  ❌ Reflow ทุกครั้งที่ update → lag เมื่อ 10 กล้อง
  ❌ ไม่เหมาะกับ 10 FPS update rate

Canvas API:
  ✅ GPU-accelerated rendering
  ✅ ไม่มี DOM reflow
  ✅ วาด bbox + zone ได้เร็วมาก
  ✅ requestAnimationFrame sync กับ browser paint cycle
```

### CameraCanvas Component (Vue)

```vue
<!-- components/CameraCanvas.vue -->
<template>
  <div class="relative">
    <canvas ref="canvas"
            :width="width" :height="height"
            class="w-full h-full" />
    <!-- Alert badge (DaisyUI) -->
    <div v-if="overlay?.alert_active"
         class="badge badge-error badge-lg absolute top-2 right-2 animate-pulse">
      ALERT
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

const props = defineProps<{
  jpegB64:  string
  overlay:  OverlayData | null
  width:    number
  height:   number
}>()

const canvas = ref<HTMLCanvasElement>()
const img    = new Image()

// Update เมื่อ frame ใหม่มา
watch(() => props.jpegB64, (b64) => {
  img.src = `data:image/jpeg;base64,${b64}`
})

img.onload = () => {
  const ctx = canvas.value?.getContext('2d')
  if (!ctx) return

  // 1. วาดภาพ
  ctx.drawImage(img, 0, 0, props.width, props.height)

  if (!props.overlay) return

  // 2. วาด Zones (polygon)
  for (const zone of props.overlay.zones) {
    ctx.beginPath()
    zone.coords.forEach(([x, y], i) => {
      const px = x * props.width
      const py = y * props.height
      i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py)
    })
    ctx.closePath()
    ctx.strokeStyle = zone.is_alert ? '#FF0000' : zone.color_hex
    ctx.lineWidth   = zone.is_alert ? 3 : 1.5
    ctx.globalAlpha = 0.7
    ctx.stroke()
    ctx.globalAlpha = 0.1
    ctx.fillStyle   = zone.color_hex
    ctx.fill()
    ctx.globalAlpha = 1.0
  }

  // 3. วาด Bounding Boxes + Labels
  for (const track of props.overlay.tracks) {
    const x1 = track.bbox.x1 * props.width
    const y1 = track.bbox.y1 * props.height
    const w  = (track.bbox.x2 - track.bbox.x1) * props.width
    const h  = (track.bbox.y2 - track.bbox.y1) * props.height

    // Box color by class
    const color = track.class_name === 'person' ? '#FF4444'
                : track.class_name === 'car'    ? '#44AAFF'
                                                : '#FFAA44'
    ctx.strokeStyle = color
    ctx.lineWidth   = 2
    ctx.strokeRect(x1, y1, w, h)

    // Label: "person #42 87% [147s]"
    const label = [
      track.class_name,
      `#${track.track_id}`,
      `${Math.round(track.confidence * 100)}%`,
      track.is_loitering ? `⚠️ ${Math.round(track.dwell_time)}s` : ''
    ].filter(Boolean).join(' ')

    ctx.fillStyle = color
    ctx.fillRect(x1, y1 - 18, label.length * 7.5, 18)
    ctx.fillStyle = '#FFFFFF'
    ctx.font      = '12px monospace'
    ctx.fillText(label, x1 + 3, y1 - 4)
  }
}
</script>
```

---

## 6. Grid Layout (10 กล้อง)

```vue
<!-- views/ConsoleView.vue — Grid section -->
<template>
  <div class="grid grid-cols-5 gap-1 h-48">
    <!-- 10 thumbnail cameras -->
    <div v-for="cam in cameras" :key="cam.id"
         class="relative cursor-pointer rounded overflow-hidden"
         :class="{
           'ring-2 ring-error ring-offset-1': cam.hasAlert,
           'ring-1 ring-success':             cam.status === 'online',
           'ring-1 ring-base-300 opacity-50': cam.status === 'offline',
           'ring-2 ring-primary':             cam.id === selectedCamId
         }"
         @click="selectCamera(cam.id)">

      <CameraCanvas
        :jpeg-b64="gridFrames[cam.id]?.jpeg_b64 ?? ''"
        :overlay="gridFrames[cam.id]?.overlay ?? null"
        :width="320" :height="180" />

      <!-- Camera name label (DaisyUI badge) -->
      <span class="badge badge-sm badge-neutral absolute bottom-1 left-1 opacity-80">
        {{ cam.name }}
      </span>

      <!-- Alert indicator -->
      <span v-if="cam.hasAlert"
            class="badge badge-error badge-xs absolute top-1 right-1 animate-ping">
      </span>
    </div>
  </div>
</template>
```

---

## 7. Performance Optimizations

### Backend

```python
# 1. ส่ง grid ทุก 333ms (3 FPS) — 1 message รวมทุกกล้อง
async def broadcast_grid(hub: WebSocketHub, cache: StreamCache):
    while True:
        frames = {}
        for cam_id in cache.active_cameras():
            cached = cache.get(cam_id)
            if cached and not cached.is_stale(max_age=1.0):
                frames[cam_id] = {
                    "jpeg_b64":  base64.b64encode(cached.thumbnail).decode(),
                    "overlay":   cached.overlay_data,
                    "status":    cached.status,
                    "timestamp": cached.timestamp,
                }
        if frames:
            await hub.broadcast_json({"type": "grid_update", "frames": frames})
        await asyncio.sleep(1/3)   # 3 FPS

# 2. Primary stream — ส่งเฉพาะกล้องที่ select
async def stream_camera(ws, camera_id: int, cache: StreamCache):
    last_ts = 0.0
    while True:
        cached = cache.get(camera_id)
        if cached and cached.timestamp > last_ts:
            await ws.send_bytes(cached.monitor)   # binary — เร็วกว่า JSON
            last_ts = cached.timestamp
        await asyncio.sleep(1/15)   # 15 FPS max
```

### Frontend

```typescript
// composables/useGridStream.ts
// ใช้ requestAnimationFrame สำหรับ render — sync กับ browser
// อย่า render ทุก WebSocket message โดยตรง

const pendingFrame = ref<GridUpdate | null>(null)

ws.onmessage = (e) => {
  pendingFrame.value = JSON.parse(e.data)  // เก็บไว้ก่อน
}

// Render loop — 60fps max, ใช้ frame ล่าสุดเท่านั้น
function renderLoop() {
  if (pendingFrame.value) {
    updateCanvases(pendingFrame.value)
    pendingFrame.value = null
  }
  requestAnimationFrame(renderLoop)
}
requestAnimationFrame(renderLoop)
```

---

## 8. UX Details ตามที่ User คาดหวัง

```
Feature                  Implementation
──────────────────────────────────────────────────────────────────
10 กล้องพร้อมกัน ไม่ lag  Grid 5×2, THUMBNAIL 3FPS, Canvas render
AI overlay               bbox (สีตาม class) + zone polygon + track ID
                         dwell time counter สำหรับ loitering
แจ้งเตือน                Alert badge กระพริบ + เสียง + LINE/Discord/Slack
แคปหลักฐาน              Auto snapshot ทุก event + 10s video clip
สอบถามภาษาธรรมชาติ      NLQ panel ← ดู 15_nlq_design.md
ตั้งค่าง่าย              Zone วาดบน Canvas ด้วย mouse drag
                         Rule config wizard (DaisyUI steps)
UI/UX                    DaisyUI theme="night" (เหมาะกลางคืน)
                         Keyboard shortcuts (Space=ACK, 1-9=switch cam)
```

---

## 9. Fullscreen & Layout Modes

```
Mode            Layout                    ใช้เมื่อ
──────────────────────────────────────────────────────────────
GRID (default)  5×2 thumbnails + alerts   ดู overview ทั้งหมด
FOCUS           1 primary + 3×3 thumbs    เมื่อเลือกกล้อง
FULLSCREEN      1 กล้อง เต็มจอ            กด F หรือ double-click
QUAD            2×2 primary feeds         ดู 4 กล้องสำคัญ
PATROL          สลับกล้องอัตโนมัติ 30s    ดูทุกกล้องแบบ sequential

สลับ mode: ปุ่มใน toolbar หรือ keyboard shortcut
```

```vue
<!-- DaisyUI tabs สำหรับ layout mode -->
<div class="tabs tabs-boxed bg-base-300 mb-2">
  <a class="tab" :class="{'tab-active': mode==='grid'}"    @click="mode='grid'">
    Grid
  </a>
  <a class="tab" :class="{'tab-active': mode==='focus'}"   @click="mode='focus'">
    Focus
  </a>
  <a class="tab" :class="{'tab-active': mode==='quad'}"    @click="mode='quad'">
    Quad
  </a>
  <a class="tab" :class="{'tab-active': mode==='patrol'}"  @click="mode='patrol'">
    Patrol
  </a>
</div>
```
