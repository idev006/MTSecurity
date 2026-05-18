<template>
  <AppLayout>
    <!-- Pilot's Console V2: Advanced Integrated Cockpit -->
    <div class="flex flex-col h-[calc(100vh-10rem)] gap-4 select-none">
      
      <div class="flex flex-col lg:flex-row gap-4 flex-1 min-h-0">
        
        <!-- ── Left Column: Visual Awareness ────────────────────────────── -->
        <div class="flex-[2] flex flex-col gap-4 min-w-0">
          
          <!-- 1. Primary Feed (Focus) with SVG Overlay -->
          <div class="card bg-black rounded-box overflow-hidden shadow-2xl border border-base-300 relative flex-1 group">
            <div v-if="primaryCamera" class="w-full h-full relative" ref="videoContainer">
              
              <!-- Live Video Stream -->
              <img :src="streamUrl(primaryCamera.id)" 
                class="w-full h-full object-contain select-none pointer-events-none"
                @load="onImageLoad"
                @error="handleStreamError" />
              
              <!-- AI & Zone SVG OVERLAY -->
              <svg 
                :key="`overlay-${primaryId}`"
                class="absolute inset-0 w-full h-full pointer-events-none z-30"
                :viewBox="`0 0 ${vWidth} ${vHeight}`"
                preserveAspectRatio="xMidYMid meet">
                
                <!-- Zone Polygons -->
                <g v-if="uiSettings.showZones">
                  <g v-for="zone in activeZones" :key="zone.id">
                    <polygon 
                      :points="scaleCoords(zone.coordinates)" 
                      :fill="hasRecentAlert(primaryId!) ? '#ff0000' : zone.color" 
                      :fill-opacity="hasRecentAlert(primaryId!) ? '0.5' : '0.25'"
                      :stroke="hasRecentAlert(primaryId!) ? '#ff0000' : zone.color"
                      :stroke-width="hasRecentAlert(primaryId!) ? 4 : 2"
                      :stroke-dasharray="hasRecentAlert(primaryId!) ? '' : '6,4'"
                      class="transition-all duration-300" />
                    <text 
                      v-if="!hasRecentAlert(primaryId!)"
                      :x="getCentroid(zone.coordinates).x" 
                      :y="getCentroid(zone.coordinates).y"
                      class="text-[10px] font-mono fill-white opacity-60 uppercase font-bold"
                      text-anchor="middle"
                      style="text-shadow: 0px 0px 3px rgba(0,0,0,1);">
                      {{ zone.name }}
                    </text>
                  </g>
                </g>

                <!-- AI Bounding Boxes (Real-time Tracks) -->
                <g v-if="uiSettings.showTracks">
                  <g v-for="track in activeTracks" :key="track.track_id">
                    <!-- Bounding Box -->
                    <rect
                      :x="track.bbox.x1 * vWidth"
                      :y="track.bbox.y1 * vHeight"
                      :width="(track.bbox.x2 - track.bbox.x1) * vWidth"
                      :height="(track.bbox.y2 - track.bbox.y1) * vHeight"
                      fill="none"
                      :stroke="hasRecentAlert(primaryId!) ? '#ff0000' : '#00A3FF'"
                      :stroke-width="hasRecentAlert(primaryId!) ? OVR.boxStrokeWidth * 2 : OVR.boxStrokeWidth"
                      class="transition-all duration-75" />

                    <!-- Centroid Dot -->
                    <circle
                      :cx="((track.bbox.x1 + track.bbox.x2) / 2) * vWidth"
                      :cy="((track.bbox.y1 + track.bbox.y2) / 2) * vHeight"
                      :r="OVR.centroidRadius"
                      :fill="hasRecentAlert(primaryId!) ? '#ff0000' : '#00A3FF'" />

                    <!-- Label HUD -->
                    <g :transform="`translate(${track.bbox.x1 * vWidth}, ${track.bbox.y1 * vHeight < OVR.labelHeight + 4 ? (track.bbox.y1 * vHeight) : (track.bbox.y1 * vHeight - OVR.labelHeight)})`">
                      <rect x="0" y="0" :width="getTextWidth(track.label, track.track_id)" :height="OVR.labelHeight"
                        :fill="hasRecentAlert(primaryId!) ? '#ff0000' : '#00A3FF'" fill-opacity="0.9" />
                      <text :x="OVR.labelPaddingX" :y="OVR.labelHeight - 3"
                        :style="`font-size:${OVR.labelFontSize}px`"
                        class="font-black fill-white font-mono uppercase tracking-tighter">
                        {{ hasRecentAlert(primaryId!) ? `🚨 ${track.label.toUpperCase()}` : `${track.label.toUpperCase()}: TRK-${track.track_id} (${Math.round(track.confidence * 100)}%)` }}
                      </text>
                    </g>
                  </g>
                </g>
              </svg>

              <!-- HUD Top Overlay -->
              <div v-if="uiSettings.showHud" class="absolute top-3 left-3 flex flex-col gap-1 pointer-events-none">
                <div class="badge badge-error gap-2 font-mono text-xs uppercase shadow-lg">
                  <span class="w-2 h-2 rounded-full bg-white animate-pulse"></span>
                  LIVE: {{ primaryCamera.name }}
                </div>
                <div class="text-[10px] font-mono text-white/70 bg-black/60 backdrop-blur px-2 py-0.5 rounded border border-white/10">
                  RES: {{ primaryCamera.resolution_width }}x{{ primaryCamera.resolution_height }} | FPS: {{ currentFps }}
                </div>
              </div>

              <!-- HUD Top Right Controls -->
              <div class="absolute top-3 right-3 flex gap-2">
                <!-- Overlay Toggles Popover -->
                <div class="dropdown dropdown-end">
                  <div tabindex="0" role="button" class="btn btn-square btn-xs btn-ghost bg-black/40 text-white hover:bg-primary border border-white/10">
                    <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
                    </svg>
                  </div>
                  <ul tabindex="0" class="dropdown-content z-[50] menu p-2 shadow-2xl bg-base-100 border border-base-300 rounded-box w-52 mt-1">
                    <li class="menu-title text-[10px] font-mono uppercase opacity-50">View Layers</li>
                    <li>
                      <label class="label cursor-pointer py-1 px-2">
                        <span class="label-text text-xs font-mono">AI TRACKS</span>
                        <input type="checkbox" v-model="uiSettings.showTracks" class="checkbox checkbox-xs checkbox-primary" />
                      </label>
                    </li>
                    <li>
                      <label class="label cursor-pointer py-1 px-2">
                        <span class="label-text text-xs font-mono">SECURITY ZONES</span>
                        <input type="checkbox" v-model="uiSettings.showZones" class="checkbox checkbox-xs checkbox-secondary" />
                      </label>
                    </li>
                    <li>
                      <label class="label cursor-pointer py-1 px-2 border-t border-base-300 mt-1 pt-2">
                        <span class="label-text text-xs font-mono">HUD INFO</span>
                        <input type="checkbox" v-model="uiSettings.showHud" class="checkbox checkbox-xs" />
                      </label>
                    </li>
                  </ul>
                </div>

                <button class="btn btn-square btn-xs btn-ghost bg-black/40 text-white hover:bg-primary border border-white/10" 
                  title="Fullscreen (F)" @click="toggleFullscreen">
                  <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4"/>
                  </svg>
                </button>
              </div>
            </div>
            
            <!-- Select Camera Placeholder -->
            <div v-else class="w-full h-full flex flex-col items-center justify-center bg-neutral text-neutral-content opacity-30">
              <svg class="h-16 w-16 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
              <p class="font-mono text-xs uppercase tracking-widest">Awaiting Video Link...</p>
            </div>
          </div>

          <!-- 2. Camera Grid (Thumbnails) -->
          <div class="h-44 flex gap-3 overflow-x-auto pb-2 scrollbar-hide">
            <div v-for="cam in cameras.cameras" :key="cam.id" 
              class="card w-60 h-full bg-base-100 border border-base-300 shadow-sm cursor-pointer hover:border-primary transition-all shrink-0 relative overflow-hidden"
              :class="cam.id === primaryId ? 'ring-2 ring-primary border-transparent' : ''"
              @click="setPrimary(cam.id)">
              
              <img :src="streamUrl(cam.id)" class="w-full h-full object-cover opacity-60 group-hover:opacity-100" />
              
              <!-- Alert Glow -->
              <div v-if="hasActiveAlert(cam.id)" class="absolute inset-0 ring-4 ring-error ring-inset animate-pulse pointer-events-none"></div>

              <!-- Footer Label -->
              <div class="absolute bottom-0 inset-x-0 bg-black/70 px-2 py-1 flex items-center justify-between border-t border-white/5">
                <span class="text-[9px] font-mono text-white/80 uppercase truncate tracking-tight">{{ cam.name }}</span>
                <span class="w-1.5 h-1.5 rounded-full" :class="dotColor(cameras.statusOf(cam.id)?.state)"></span>
              </div>
            </div>
          </div>
        </div>

        <!-- ── Right Column: Situational Awareness ──────────────────────── -->
        <div class="w-full lg:w-[400px] flex flex-col gap-4">
          
          <!-- 3. Alert Queue -->
          <div class="card bg-base-100 border border-base-300 shadow-2xl flex-1 min-h-0 overflow-hidden"
            :class="events.newCount > 0 ? 'border-error/40' : ''">
            <!-- Queue header -->
            <div class="p-3 border-b border-base-300 flex items-center justify-between bg-base-200/50 backdrop-blur-sm">
              <div class="flex items-center gap-2">
                <span v-if="events.newCount > 0"
                  class="inline-block w-2 h-2 rounded-full bg-error status-breathe"></span>
                <span v-else class="inline-block w-2 h-2 rounded-full bg-success status-breathe"></span>
                <h2 class="font-bold text-[11px] font-mono tracking-tight uppercase">
                  ALERT QUEUE
                </h2>
                <span class="badge badge-xs font-mono"
                  :class="events.newCount > 0 ? 'badge-error' : 'badge-ghost'">
                  {{ events.newCount }}
                </span>
              </div>
              <div class="flex gap-1">
                <button class="btn btn-ghost btn-xs text-[9px] font-mono opacity-50 hover:opacity-100" @click="toggleFilters">FILTERS</button>
                <button class="btn btn-ghost btn-xs text-[9px] font-mono text-success hover:text-success" @click="events.ackAll()">ACK ALL</button>
              </div>
            </div>

            <!-- Filters Bar (Expandable) -->
            <div v-if="showFilters" class="p-2 bg-base-200/30 border-b border-base-300 flex gap-2">
              <select v-model="filters.severity" class="select select-bordered select-xs font-mono text-[9px] flex-1">
                <option value="">ALL SEVERITY</option>
                <option value="critical">CRITICAL</option>
                <option value="high">HIGH</option>
                <option value="medium">MEDIUM</option>
              </select>
              <button class="btn btn-xs font-mono text-[9px]" @click="filters.unackedOnly = !filters.unackedOnly"
                :class="filters.unackedOnly ? 'btn-primary' : 'btn-ghost border-base-300'">
                UNACKED
              </button>
            </div>

            <!-- Alert items with left color strip -->
            <div class="flex-1 overflow-y-auto divide-y divide-base-200 scrollbar-thin">
              <div v-for="ev in filteredAlerts" :key="ev.id"
                class="flex group hover:bg-base-200/40 transition-colors relative"
                :class="ev.status !== 'NEW' ? 'opacity-50' : ''">
                <!-- Left severity strip -->
                <div class="w-1 shrink-0 rounded-tl rounded-bl"
                  :class="ev.severity === 'critical' ? 'bg-error' : ev.severity === 'high' ? 'bg-warning' : ev.severity === 'medium' ? 'bg-info' : 'bg-base-300'">
                </div>

                <!-- Content -->
                <div class="flex-1 px-3 py-2.5 min-w-0">
                  <!-- Line 1: severity badge + behavior + camera badge right -->
                  <div class="flex items-center gap-1.5 mb-0.5">
                    <span class="badge badge-xs font-mono shrink-0"
                      :class="ev.severity === 'critical' ? 'badge-error' : ev.severity === 'high' ? 'badge-warning' : ev.severity === 'medium' ? 'badge-info' : 'badge-ghost'">
                      {{ ev.severity.toUpperCase() }}
                    </span>
                    <span class="text-xs font-bold capitalize truncate flex-1">{{ ev.behavior.replace(/_/g, ' ') }}</span>
                    <span class="badge badge-xs badge-ghost font-mono shrink-0">CAM {{ ev.camera_id }}</span>
                  </div>
                  <!-- Line 2: confidence + relative time -->
                  <div class="flex items-center gap-2 text-[10px] font-mono opacity-40">
                    <span>{{ (ev.confidence * 100).toFixed(0) }}% CONF</span>
                    <span>·</span>
                    <span>{{ fmtTime(ev.occurred_at) }}</span>
                  </div>
                  <!-- Hover-reveal actions -->
                  <div class="flex gap-1.5 mt-2">
                    <button class="btn btn-xs btn-outline btn-primary font-mono text-[9px]" @click="setPrimary(ev.camera_id)">
                      VIEW
                    </button>
                    <button v-if="ev.status === 'NEW'"
                      class="btn btn-xs btn-success font-mono text-[9px]"
                      :disabled="acking.has(ev.id)"
                      @click="ack(ev.id)">
                      ✓ ACK
                    </button>
                  </div>
                </div>
              </div>

              <!-- Empty state — full height centered, green glow -->
              <div v-if="filteredAlerts.length === 0"
                class="flex flex-col items-center justify-center h-full py-16 gap-3">
                <div class="w-12 h-12 rounded-full bg-success/10 flex items-center justify-center glow-success">
                  <svg class="h-6 w-6 text-success" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                </div>
                <div class="text-center">
                  <p class="text-xs font-mono font-bold text-success">ALL CLEAR</p>
                  <p class="text-[10px] font-mono opacity-30 mt-0.5">NO ACTIVE ALERTS</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 4. Real-time System Telemetry — DaisyUI stats layout -->
          <div class="card bg-base-100 border border-base-300 shadow-2xl overflow-hidden">
            <!-- Header -->
            <div class="px-4 py-2 border-b border-base-300 bg-base-200/50">
              <p class="text-[9px] font-mono tracking-[0.3em] opacity-40 uppercase">System Telemetry</p>
            </div>

            <!-- 3-column stats -->
            <div class="stats stats-horizontal w-full divide-x divide-base-300 shadow-none border-b border-base-300">
              <!-- CPU -->
              <div class="stat px-3 py-2.5">
                <div class="stat-title font-mono text-[9px] tracking-widest opacity-40">CPU</div>
                <div class="stat-value text-lg font-mono" :class="gaugeColor(system.cpuPercent)">
                  {{ system.cpuPercent.toFixed(0) }}<span class="text-xs opacity-50">%</span>
                </div>
                <div class="stat-desc w-full mt-1">
                  <progress class="progress progress-xs w-full" :class="progressClass(system.cpuPercent)"
                    :value="system.cpuPercent" max="100"></progress>
                </div>
              </div>
              <!-- RAM -->
              <div class="stat px-3 py-2.5">
                <div class="stat-title font-mono text-[9px] tracking-widest opacity-40">RAM</div>
                <div class="stat-value text-lg font-mono" :class="gaugeColor(system.ramPercent)">
                  {{ system.ramPercent.toFixed(0) }}<span class="text-xs opacity-50">%</span>
                </div>
                <div class="stat-desc w-full mt-1">
                  <progress class="progress progress-xs w-full" :class="progressClass(system.ramPercent)"
                    :value="system.ramPercent" max="100"></progress>
                </div>
              </div>
              <!-- Cameras -->
              <div class="stat px-3 py-2.5">
                <div class="stat-title font-mono text-[9px] tracking-widest opacity-40">CAMERAS</div>
                <div class="stat-value text-lg font-mono"
                  :class="system.camerasOnline === system.camerasTotal ? 'text-success' : 'text-warning'">
                  {{ system.camerasOnline }}<span class="text-xs opacity-40">/{{ system.camerasTotal }}</span>
                </div>
                <div class="stat-desc font-mono text-[9px] mt-1 opacity-50">ONLINE</div>
              </div>
            </div>

            <!-- Uptime + shortcuts -->
            <div class="px-4 py-2.5 space-y-2">
              <div class="flex items-center justify-between text-[10px] font-mono opacity-40">
                <span>UPTIME</span>
                <span>{{ system.uptime }}</span>
              </div>
              <div class="border-t border-base-300 pt-2 flex flex-wrap gap-x-3 gap-y-1.5 opacity-40">
                <span class="flex items-center gap-1">
                  <kbd class="kbd kbd-xs font-mono">SPACE</kbd>
                  <span class="text-[9px] font-mono">ACK LATEST</span>
                </span>
                <span class="flex items-center gap-1">
                  <kbd class="kbd kbd-xs font-mono">1-9</kbd>
                  <span class="text-[9px] font-mono">SWITCH CAM</span>
                </span>
                <span class="flex items-center gap-1">
                  <kbd class="kbd kbd-xs font-mono">F</kbd>
                  <span class="text-[9px] font-mono">FULLSCREEN</span>
                </span>
                <span class="flex items-center gap-1">
                  <kbd class="kbd kbd-xs font-mono">ESC</kbd>
                  <span class="text-[9px] font-mono">CLOSE</span>
                </span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- ── Evidence Snapshot Modal ────────────────────────────────────── -->
    <dialog id="alert_modal" class="modal">
      <div class="modal-box max-w-3xl bg-base-100 border border-base-300 p-0 overflow-hidden shadow-2xl">
        <div v-if="activeAlert" class="flex flex-col">
          <!-- Header -->
          <div class="bg-error text-error-content p-4 flex justify-between items-center">
            <h3 class="font-black font-mono uppercase tracking-tight flex items-center gap-3">
              <svg class="h-5 w-5 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
              </svg>
              {{ activeAlert.behavior.replace('_', ' ') }} DETECTED
            </h3>
            <span class="text-xs font-mono font-bold">{{ fmtTime(activeAlert.occurred_at) }}</span>
          </div>
          
          <div class="flex flex-col md:flex-row">
            <!-- Image Area -->
            <div class="flex-1 bg-black aspect-video flex items-center justify-center relative group">
              <img v-if="activeAlert.snapshot_url" 
                :src="`${activeAlert.snapshot_url}?token=${auth.token}`" 
                class="w-full h-full object-contain" />
              <div v-else class="text-white/20 font-mono text-xs italic">IMAGE UNAVAILABLE</div>
              
              <!-- Zoom Indicator -->
              <div class="absolute bottom-2 right-2 bg-black/60 px-2 py-1 text-[10px] font-mono text-white opacity-0 group-hover:opacity-100">
                AI CONFIDENCE: {{ (activeAlert.confidence * 100).toFixed(0) }}%
              </div>
            </div>

            <!-- Meta Area -->
            <div class="w-full md:w-80 p-6 border-l border-base-300 bg-base-100 flex flex-col gap-6">
              <div>
                <label class="text-[10px] font-mono opacity-40 block mb-1.5 uppercase tracking-widest">Incident Source</label>
                <div class="text-base font-black">{{ camName(activeAlert.camera_id) }}</div>
                <div class="text-[10px] font-mono opacity-60">SENSOR_ID: CAM-00{{ activeAlert.camera_id }}</div>
              </div>

              <div>
                <label class="text-[10px] font-mono opacity-40 block mb-2 uppercase tracking-widest">Operational Notes</label>
                <textarea class="textarea textarea-bordered textarea-sm w-full font-mono h-24 text-xs" 
                  v-model="ackNote"
                  placeholder="Enter resolution details..."></textarea>
              </div>

              <div class="flex flex-col gap-2 mt-auto">
                <button class="btn btn-success font-mono w-full shadow-lg" 
                  :disabled="acking.has(activeAlert.id)"
                  @click="ack(activeAlert!.id, ackNote); closeModal()">RESOLVE INCIDENT</button>
                <button class="btn btn-ghost btn-sm font-mono w-full opacity-50" @click="closeModal">DISMISS</button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop bg-black/80 backdrop-blur-sm">
        <button @click="closeModal">close</button>
      </form>
    </dialog>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import { useCamerasStore } from '@/stores/cameras'
import { useEventsStore } from '@/stores/events'
import { useSystemStore } from '@/stores/system'
import { useAuthStore } from '@/stores/auth'
import { useZonesStore } from '@/stores/zones'
import { UI_CONFIG } from '@/config/uiConfig'
import { parseUtcIso } from '@/utils/time'

const OVR = UI_CONFIG.overlay

const cameras = useCamerasStore()
const events  = useEventsStore()
const system  = useSystemStore()
const auth    = useAuthStore()
const zones   = useZonesStore()

const primaryId = ref<number | null>(null)
const acking = ref<Set<number>>(new Set())
const activeAlert = ref<any>(null)
const ackNote = ref('')
const showFilters = ref(false)
const filters = ref({ severity: '', unackedOnly: true })

// HUD / Overlay Settings
const uiSettings = ref({
  showTracks: true,
  showZones: true,
  showHud: true
})

// Timer to force re-evaluation of alert flashes
const now = ref(Date.now())
let flashTimer: ReturnType<typeof setInterval>

// HUD state
const imgLoaded = ref(false)
const vWidth = ref(1280)
const vHeight = ref(720)
const videoContainer = ref<HTMLElement | null>(null)

// Computed
const primaryCamera = computed(() => 
  cameras.cameras.find(c => c.id === primaryId.value) || cameras.cameras[0]
)

const activeZones = computed(() => {
  if (!primaryId.value) return []
  return zones.zones.filter(z => Number(z.camera_id) === Number(primaryId.value) && z.is_active)
})

const activeTracks = computed(() => {
  if (!primaryId.value) return []
  return cameras.statusOf(primaryId.value)?.tracks || []
})

const currentFps = computed(() => {
  if (!primaryId.value) return 0
  return cameras.statusOf(primaryId.value)?.fps?.toFixed(1) || 0
})

const filteredAlerts = computed(() => {
  return events.events.filter(e => {
    if (filters.value.severity && e.severity !== filters.value.severity) return false
    if (filters.value.unackedOnly && e.status !== 'NEW') return false
    return true
  }).slice(0, 20)
})

// ── Actions ──────────────────────────────────────────────────────────────────

function setPrimary(id: number) {
  primaryId.value = id
  imgLoaded.value = false
  
  // 1. Clear old tracks for a clean transition
  cameras.patchStatus(id, { tracks: [] })
  
  // 2. Subscribe to this camera's high-res stream and metadata
  // We send the ID as an array. The backend hub expects a list of IDs.
  system.subscribeCamera([id])
  
  console.log(`[Pilot] Switched to Camera ${id}, requesting AI metadata...`)
}

async function ack(id: number, note?: string) {
  acking.value.add(id)
  try { 
    await events.acknowledge(id, note)
    ackNote.value = ''
  } finally { 
    acking.value.delete(id) 
  }
}

// ── UI Logic ─────────────────────────────────────────────────────────────────

function onImageLoad(e: Event) {
  const img = e.target as HTMLImageElement
  vWidth.value = img.naturalWidth
  vHeight.value = img.naturalHeight
  imgLoaded.value = true
}

function scaleCoords(coords: any) {
  try {
    // If it's a string (old format), parse it. If it's already an array, use it.
    const points = typeof coords === 'string' ? JSON.parse(coords) : coords
    if (!Array.isArray(points) || !points.length) return ""
    
    return points.map(c => `${(c[0] * vWidth.value).toFixed(1)},${(c[1] * vHeight.value).toFixed(1)}`).join(' ')
  } catch (e) { 
    console.error('[Pilot] Scale error:', e)
    return "" 
  }
}

function getCentroid(coords: any) {
  try {
    const points = typeof coords === 'string' ? JSON.parse(coords) : coords
    if (!Array.isArray(points) || !points.length) return { x: 0, y: 0 }
    
    const x = points.reduce((a, b) => a + b[0], 0) / points.length
    const y = points.reduce((a, b) => a + b[1], 0) / points.length
    return { x: x * vWidth.value, y: y * vHeight.value }
  } catch { return { x: 0, y: 0 } }
}

function getTrackColor(label: string) {
  const colors: Record<string, string> = {
    person: '#ff4757', // Red
    car: '#eccc68',    // Yellow
    truck: '#ffa502',  // Orange
    bicycle: '#2ed573',// Green
    default: '#1e90ff' // Blue
  }
  return colors[label.toLowerCase()] || colors.default
}

function getTextWidth(label: string, id: number) {
  return (`#${id} ${label}`.length * OVR.labelCharWidth) + OVR.labelPaddingX * 2
}

function closeModal() {
  const modal = document.getElementById('alert_modal') as HTMLDialogElement
  modal?.close()
  activeAlert.value = null
}

function openModal(ev: any) {
  activeAlert.value = ev
  const modal = document.getElementById('alert_modal') as HTMLDialogElement
  modal?.showModal()
}

function toggleFilters() {
  showFilters.value = !showFilters.value
}

function toggleFullscreen() {
  const el = videoContainer.value
  if (el?.requestFullscreen) el.requestFullscreen()
}

// ── Keyboard Shortcuts ──────────────────────────────────────────────────────

function handleKeydown(e: KeyboardEvent) {
  if (e.target instanceof HTMLTextAreaElement || e.target instanceof HTMLInputElement) return

  // 1-9 to switch cameras
  if (e.key >= '1' && e.key <= '9') {
    const idx = parseInt(e.key) - 1
    if (cameras.cameras[idx]) setPrimary(cameras.cameras[idx].id)
  }
  // 0 for 10th
  if (e.key === '0' && cameras.cameras[9]) setPrimary(cameras.cameras[9].id)

  // Space to ACK latest NEW alert
  if (e.key === ' ' || e.code === 'Space') {
    e.preventDefault()
    const latest = events.events.find(e => e.status === 'NEW')
    if (latest) ack(latest.id, 'Shortcut ACK')
  }

  // F for fullscreen
  if (e.key.toLowerCase() === 'f') toggleFullscreen()
  
  // Esc to close modal
  if (e.key === 'Escape') closeModal()
}

// ── Lifecycle ────────────────────────────────────────────────────────────────

onMounted(async () => {
  await Promise.all([
    cameras.fetchAll(),
    events.fetchRecent(),
    zones.fetchAll()
  ])
  
  if (cameras.cameras.length > 0) {
    setPrimary(cameras.cameras[0].id)
  }

  flashTimer = setInterval(() => now.value = Date.now(), 500)
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  clearInterval(flashTimer)
  window.removeEventListener('keydown', handleKeydown)
})

// Watchers
watch(() => events.events[0], (newAlert) => {
  if (newAlert && newAlert.status === 'NEW') {
    if (newAlert.severity === 'high' || newAlert.severity === 'critical') {
      openModal(newAlert)
    }
  }
}, { deep: true })

// ── Formatting ────────────────────────────────────────────────────────────

function hasRecentAlert(cameraId: number): boolean {
  const currentMs = now.value
  const recent = events.events.find(e => e.camera_id === cameraId)
  if (!recent) return false
  const ageSecs = (currentMs - parseUtcIso(recent.occurred_at).getTime()) / 1000
  return ageSecs < 3.0 // Flash for 3 seconds
}

function streamUrl(id: number) {
  return `${import.meta.env.VITE_API_BASE || ''}/api/v1/cameras/${id}/stream?token=${auth.token}`
}

function camName(id: number) {
  return cameras.cameras.find(c => c.id === id)?.name || `CAM ${id}`
}

function hasActiveAlert(camId: number) {
  return events.events.some(a => a.camera_id === camId && a.status === 'NEW')
}

function fmtTime(iso: string) {
  if (!iso) return '--:--:--'
  const d = parseUtcIso(iso)
  if (isNaN(d.getTime())) return iso
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function sevClass(s: string) {
  return {
    critical: 'bg-error text-error-content animate-pulse',
    high:     'bg-error text-error-content',
    medium:   'bg-warning text-warning-content',
    low:      'bg-neutral text-neutral-content',
  }[s] ?? 'bg-neutral'
}

function dotColor(state?: string) {
  return {
    ONLINE:       'bg-success',
    RECONNECTING: 'bg-warning animate-pulse',
    ERROR:        'bg-error',
    FAILED:       'bg-error',
    INACTIVE:     'bg-base-300',
  }[state ?? ''] ?? 'bg-base-300'
}

function progressClass(pct: number) {
  if (pct >= 90) return 'progress-error'
  if (pct >= 70) return 'progress-warning'
  return 'progress-success'
}

function gaugeColor(pct: number) {
  if (pct >= 90) return 'text-error font-bold'
  if (pct >= 70) return 'text-warning font-bold'
  return ''
}

function handleStreamError(e: Event) {
  // Silent fallback
}
</script>

<style scoped>
.scrollbar-hide::-webkit-scrollbar { display: none; }
.scrollbar-thin::-webkit-scrollbar { width: 4px; }
.scrollbar-thin::-webkit-scrollbar-thumb { background: #333; border-radius: 10px; }

/* HUD Animations */
.group:hover .badge { transform: scale(1.05); }
.transition-all { transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1); }

/* SVG Optimization */
svg rect, svg polygon {
  vector-effect: non-scaling-stroke;
}
</style>
