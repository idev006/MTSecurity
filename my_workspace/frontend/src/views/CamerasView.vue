<template>
  <AppLayout>
    <div class="flex flex-col gap-4">

      <!-- ── Toolbar ──────────────────────────────────────────────────── -->
      <div class="flex items-center gap-2 flex-wrap">
        <div class="ml-auto flex items-center gap-1.5 flex-wrap">
          <!-- Layout toggle -->
          <div class="join">
            <button class="btn btn-xs join-item font-mono"
              :class="layout === 'grid' ? 'btn-neutral' : 'btn-ghost'"
              @click="layout = 'grid'">
              <svg class="h-3 w-3" fill="currentColor" viewBox="0 0 16 16">
                <rect x="1" y="1" width="6" height="6" rx="1"/><rect x="9" y="1" width="6" height="6" rx="1"/>
                <rect x="1" y="9" width="6" height="6" rx="1"/><rect x="9" y="9" width="6" height="6" rx="1"/>
              </svg>
              GRID
            </button>
            <button class="btn btn-xs join-item font-mono"
              :class="layout === 'list' ? 'btn-neutral' : 'btn-ghost'"
              @click="layout = 'list'">
              <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
              </svg>
              LIST
            </button>
          </div>

          <!-- State filter -->
          <select class="select select-xs select-bordered font-mono" v-model="filterState">
            <option value="">ALL STATES</option>
            <option value="ONLINE">ONLINE</option>
            <option value="CONNECTING">CONNECTING</option>
            <option value="RECONNECTING">RECONNECTING</option>
            <option value="ERROR">ERROR</option>
            <option value="FAILED">FAILED</option>
            <option value="INACTIVE">INACTIVE</option>
          </select>

          <!-- Overlays toggle -->
          <label class="flex items-center gap-1.5 cursor-pointer px-2 py-0.5 rounded hover:bg-base-200">
            <input type="checkbox" v-model="showOverlays" class="toggle toggle-xs toggle-primary" />
            <span class="text-xs font-mono opacity-60">OVERLAYS</span>
          </label>

          <!-- Refresh -->
          <button class="btn btn-xs btn-square btn-ghost opacity-60 hover:opacity-100"
            title="Refresh" @click="cameras.fetchAll()">
            <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
            </svg>
          </button>

          <!-- Add webcam -->
          <button class="btn btn-xs btn-primary font-mono gap-1" @click="openAddWebcam">
            <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
            </svg>
            WEBCAM
          </button>
        </div>
      </div>

      <!-- ── Summary strip ────────────────────────────────────────────── -->
      <div class="flex items-center gap-2 flex-wrap">
        <span class="badge badge-xs badge-success font-mono gap-1">
          <span class="w-1.5 h-1.5 rounded-full bg-success animate-pulse"></span>
          {{ cameras.online }} ONLINE
        </span>
        <span v-if="cameras.reconnecting" class="badge badge-xs badge-warning font-mono gap-1">
          {{ cameras.reconnecting }} RECONN
        </span>
        <span v-if="cameras.failed" class="badge badge-xs badge-error font-mono gap-1">
          {{ cameras.failed }} ERROR
        </span>
        <span class="badge badge-xs badge-ghost font-mono">{{ cameras.total }} TOTAL</span>
        <span v-if="webcamCount" class="badge badge-xs badge-info font-mono">{{ webcamCount }} USB</span>
      </div>

      <!-- ── Loading ───────────────────────────────────────────────────── -->
      <div v-if="cameras.loading" class="flex justify-center py-12">
        <span class="loading loading-spinner loading-md opacity-40"></span>
      </div>

      <!-- ── Empty state ───────────────────────────────────────────────── -->
      <div v-else-if="filtered.length === 0 && !cameras.loading"
        class="flex flex-col items-center py-16 opacity-30 gap-2">
        <svg class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1"
            d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
        </svg>
        <p class="font-mono text-sm">NO CAMERAS MATCH</p>
        <button class="btn btn-xs btn-primary font-mono mt-2" @click="openAddWebcam">+ ADD WEBCAM</button>
      </div>

      <!-- ── Grid layout ───────────────────────────────────────────────── -->
      <div v-else-if="layout === 'grid'"
        class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        <div v-for="cam in filtered" :key="cam.id"
          class="group rounded-lg border bg-base-100 overflow-hidden cursor-pointer transition-all hover:shadow-md"
          :class="cardBorder(cameras.statusOf(cam.id)?.state)"
          @click="selectCam(cam.id)">

          <!-- Video area — MJPEG when ONLINE, placeholder when offline -->
          <div class="aspect-video bg-base-300 flex items-center justify-center relative overflow-hidden transition-colors duration-300"
               :class="{ 'ring-4 ring-inset ring-error shadow-[inset_0_0_20px_rgba(255,0,0,0.5)]': hasRecentAlert(cam.id) }">

            <!-- Live MJPEG stream (browser handles multipart natively) -->
            <img v-if="cameras.statusOf(cam.id)?.state === 'ONLINE'"
              :src="streamUrl(cam.id)"
              class="absolute inset-0 w-full h-full object-cover"
              alt="live feed" />

            <!-- Zones Overlay -->
            <svg class="absolute inset-0 w-full h-full pointer-events-none"
                 v-if="showOverlays && cameras.statusOf(cam.id)?.state === 'ONLINE'"
                 viewBox="0 0 100 100" preserveAspectRatio="none">
              <g v-for="z in zonesByCamera(cam.id)" :key="z.id">
                <polygon :points="formatZonePoints(z.coordinates)"
                         :fill="hasRecentAlert(cam.id) ? '#ff0000' : z.color"
                         :fill-opacity="hasRecentAlert(cam.id) ? '0.4' : '0.15'"
                         :stroke="hasRecentAlert(cam.id) ? '#ff0000' : z.color"
                         :stroke-width="hasRecentAlert(cam.id) ? '1' : '0.6'"
                         :stroke-dasharray="hasRecentAlert(cam.id) ? '' : '2,2'"
                         class="transition-all duration-300" />
                <text v-if="!hasRecentAlert(cam.id)"
                      :x="getZoneLabelPos(z.coordinates).x + 1" 
                      :y="getZoneLabelPos(z.coordinates).y + 3"
                      :fill="z.color" font-size="2.5" font-family="monospace" font-weight="bold"
                      style="text-shadow: 0px 0px 2px rgba(0,0,0,0.8);">
                  {{ z.name }}
                </text>
              </g>
            </svg>

            <!-- AI Bounding Boxes overlay -->
            <svg class="absolute inset-0 w-full h-full pointer-events-none"
                 v-if="showOverlays && cameras.statusOf(cam.id)?.state === 'ONLINE'"
                 viewBox="0 0 100 100" preserveAspectRatio="none">
              <g v-for="t in (cameras.statusOf(cam.id) as any).tracks || []" :key="t.track_id">
                <rect :x="t.bbox.x1 * 100" :y="t.bbox.y1 * 100"
                      :width="(t.bbox.x2 - t.bbox.x1) * 100"
                      :height="(t.bbox.y2 - t.bbox.y1) * 100"
                      fill="none" :stroke="hasRecentAlert(cam.id) ? '#ff0000' : '#00A3FF'" :stroke-width="hasRecentAlert(cam.id) ? '0.8' : '0.5'" />
                <rect :x="t.bbox.x1 * 100" 
                      :y="(t.bbox.y1 * 100) < 5 ? (t.bbox.y1 * 100) : (t.bbox.y1 * 100) - 3.5"
                      :width="hasRecentAlert(cam.id) ? 35 : 30" height="3.5"
                      :fill="hasRecentAlert(cam.id) ? '#ff0000' : '#00A3FF'" fill-opacity="0.8" />
                <text :x="(t.bbox.x1 * 100) + 0.5" 
                      :y="(t.bbox.y1 * 100) < 5 ? (t.bbox.y1 * 100) + 2.5 : (t.bbox.y1 * 100) - 1"
                      fill="#ffffff" font-size="2.5" font-family="monospace" font-weight="bold">
                  {{ hasRecentAlert(cam.id) ? `🚨 ${t.label.toUpperCase()}` : `${t.label.toUpperCase()}: TRK-${t.track_id} (${Math.round(t.confidence * 100)}%)` }}
                </text>
                <!-- Centroid dot (The exact point used for Zone intersection) -->
                <circle :cx="((t.bbox.x1 + t.bbox.x2) / 2) * 100" 
                        :cy="((t.bbox.y1 + t.bbox.y2) / 2) * 100" 
                        r="0.8" :fill="hasRecentAlert(cam.id) ? '#ff0000' : '#00A3FF'" />
              </g>
            </svg>

            <!-- Offline placeholder -->
            <div v-else class="text-center opacity-30">
              <svg class="h-7 w-7 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
            </div>

            <!-- State badge overlay -->
            <div class="absolute top-1.5 left-1.5 flex gap-1 z-10">
              <span class="badge badge-xs font-mono" :class="stateBadge(cameras.statusOf(cam.id)?.state)">
                {{ cameras.statusOf(cam.id)?.state ?? 'INACTIVE' }}
              </span>
              <span v-if="cam.source_type === 'webcam'" class="badge badge-xs badge-info font-mono">USB</span>
            </div>
            <!-- FPS overlay -->
            <div v-if="cameras.statusOf(cam.id)?.fps"
              class="absolute bottom-1.5 right-1.5 text-xs font-mono opacity-60 bg-base-100/70 px-1 rounded z-10">
              {{ cameras.statusOf(cam.id)?.fps?.toFixed(0) }}fps
            </div>

            <!-- Edit / Delete actions — reveal on card hover -->
            <div class="absolute top-1.5 right-1.5 flex gap-1 z-20"
                 @click.stop>
              <div class="tooltip tooltip-left" data-tip="Edit camera">
                <button class="btn btn-xs btn-square bg-base-100/80 hover:btn-primary border-0"
                  @click="openEditCam(cam)">
                  <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                  </svg>
                </button>
              </div>
              <div class="tooltip tooltip-left" data-tip="Delete camera">
                <button class="btn btn-xs btn-square bg-base-100/80 hover:btn-error border-0"
                  @click="openDeleteCam(cam)">
                  <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                </button>
              </div>
            </div>

            <!-- Security Status Widget -->
            <div v-if="cameras.statusOf(cam.id)?.state === 'ONLINE' && zonesByCamera(cam.id).length > 0"
                 class="absolute bottom-1.5 left-1.5 flex items-center gap-1.5 px-2 py-0.5 rounded backdrop-blur-md border shadow-lg transition-colors z-10"
                 :class="hasRecentAlert(cam.id) ? 'bg-error/20 border-error text-error animate-pulse' : 'bg-base-300/80 border-success/50 text-success'">
              <svg v-if="hasRecentAlert(cam.id)" class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <svg v-else class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <span class="text-[10px] font-mono font-bold tracking-wider">
                {{ recentAlertFor(cam.id) ? `ALERT: ${recentAlertFor(cam.id)!.behavior.replace(/_/g, ' ').toUpperCase()}` : `SECURE (${zonesByCamera(cam.id).length} ZONE)` }}
              </span>
            </div>
          </div>


          <!-- Info strip footer -->
          <div class="px-2 py-1.5 flex items-center justify-between gap-1 border-t border-base-300 bg-base-200/40">
            <div class="min-w-0 flex-1">
              <p class="text-xs font-semibold truncate">{{ cam.name }}</p>
              <p class="text-[10px] opacity-40 font-mono truncate">
                {{ cam.location || (cam.source_type === 'webcam' ? `USB DEV ${cam.device_index}` : 'RTSP') }}
              </p>
            </div>
            <div class="flex items-center gap-1.5 shrink-0" @click.stop>
              <input type="checkbox" class="toggle toggle-xs toggle-success"
                :checked="cam.is_active"
                :disabled="toggling.has(cam.id)"
                @change="toggleCam(cam.id, ($event.target as HTMLInputElement).checked)"
                title="Enable / Disable camera" />
              <span class="inline-block w-2 h-2 rounded-full"
                :class="dotColor(cameras.statusOf(cam.id)?.state)"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- ── List layout ───────────────────────────────────────────────── -->
      <div v-else class="card bg-base-100 border border-base-300 shadow-none overflow-hidden">
        <table class="table table-sm table-pin-rows">
          <thead>
            <tr class="font-mono text-xs opacity-50 border-b border-base-300">
              <th>ID</th><th>NAME</th><th>SOURCE</th><th>LOCATION</th>
              <th>STATE</th><th>FPS</th><th>LATENCY</th><th>LAST FRAME</th>
              <th>ON/OFF</th><th class="text-right pr-3">ACTIONS</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="cam in filtered" :key="cam.id"
              class="hover border-b border-base-300/50 last:border-0"
              :class="cameras.statusOf(cam.id)?.state === 'ERROR' ? 'bg-error/5' : ''">
              <td class="font-mono text-xs opacity-50">{{ cam.id }}</td>
              <td class="font-semibold text-sm">{{ cam.name }}</td>
              <td>
                <span class="badge badge-xs font-mono"
                  :class="cam.source_type === 'webcam' ? 'badge-info' : 'badge-ghost'">
                  {{ cam.source_type === 'webcam' ? `USB:${cam.device_index}` : 'RTSP' }}
                </span>
              </td>
              <td class="text-xs opacity-60">{{ cam.location ?? '—' }}</td>
              <td>
                <span class="badge badge-xs font-mono" :class="stateBadge(cameras.statusOf(cam.id)?.state)">
                  {{ cameras.statusOf(cam.id)?.state ?? 'INACTIVE' }}
                </span>
              </td>
              <td class="font-mono text-xs">{{ cameras.statusOf(cam.id)?.fps?.toFixed(0) ?? '—' }}</td>
              <td class="font-mono text-xs">
                {{ cameras.statusOf(cam.id)?.latency_ms ? cameras.statusOf(cam.id)!.latency_ms.toFixed(0) + 'ms' : '—' }}
              </td>
              <td class="font-mono text-xs opacity-50">
                {{ cameras.statusOf(cam.id)?.last_frame_at ? fmtTime(cameras.statusOf(cam.id)!.last_frame_at!) : '—' }}
              </td>
              <!-- Enable / Disable toggle -->
              <td>
                <input type="checkbox" class="toggle toggle-xs toggle-success"
                  :checked="cam.is_active"
                  :disabled="toggling.has(cam.id)"
                  @change="toggleCam(cam.id, ($event.target as HTMLInputElement).checked)" />
              </td>
              <!-- Action buttons -->
              <td class="text-right pr-2">
                <div class="flex gap-1 justify-end items-center">
                  <!-- Error info -->
                  <div v-if="cameras.statusOf(cam.id)?.error_msg"
                    class="tooltip tooltip-left" :data-tip="cameras.statusOf(cam.id)?.error_msg">
                    <button class="btn btn-xs btn-square btn-error btn-ghost">
                      <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                      </svg>
                    </button>
                  </div>
                  <!-- View live in Pilot -->
                  <div class="tooltip tooltip-left" data-tip="View live in Pilot">
                    <RouterLink :to="{ path: '/pilot', query: { cam: cam.id } }"
                      class="btn btn-xs btn-square btn-ghost">
                      <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                      </svg>
                    </RouterLink>
                  </div>
                  <!-- View stream (MJPEG) in new tab -->
                  <div class="tooltip tooltip-left" data-tip="Open stream">
                    <a :href="streamUrl(cam.id)" target="_blank"
                      class="btn btn-xs btn-square btn-ghost"
                      :class="cameras.statusOf(cam.id)?.state !== 'ONLINE' ? 'opacity-30' : ''">
                      <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                      </svg>
                    </a>
                  </div>
                  <!-- Edit -->
                  <div class="tooltip tooltip-left" data-tip="Edit camera">
                    <button class="btn btn-xs btn-square btn-ghost" @click="openEditCam(cam)">
                      <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                      </svg>
                    </button>
                  </div>
                  <!-- Delete -->
                  <div class="tooltip tooltip-left" data-tip="Delete camera">
                    <button class="btn btn-xs btn-square btn-ghost text-error hover:btn-error" @click="openDeleteCam(cam)">
                      <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                      </svg>
                    </button>
                  </div>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

    </div>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- ADD WEBCAM MODAL                                                       -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <dialog ref="webcamModal" class="modal">
      <div class="modal-box max-w-sm">
        <!-- Header -->
        <h3 class="font-mono font-bold text-sm mb-4">+ ADD WEBCAM</h3>

        <!-- Probe status -->
        <div v-if="probing" class="flex items-center gap-2 text-xs font-mono opacity-60 mb-4">
          <span class="loading loading-spinner loading-xs"></span>
          SCANNING DEVICES 0-9…
        </div>
        <div v-else-if="availableWebcams.length === 0 && !probing"
          class="alert alert-warning text-xs font-mono p-2 mb-4">
          No webcam devices detected. Connect a USB webcam and try again.
        </div>

        <!-- Device picker -->
        <div v-if="availableWebcams.length > 0" class="form-control mb-3">
          <label class="label py-1">
            <span class="label-text font-mono text-xs opacity-60">DEVICE</span>
          </label>
          <div class="grid grid-cols-5 gap-2">
            <button v-for="dev in availableWebcams" :key="dev.index"
              class="btn btn-sm font-mono"
              :class="form.device_index === dev.index ? 'btn-primary' : 'btn-outline'"
              @click="form.device_index = dev.index; form.device_name = dev.device_name">
              {{ dev.index }}
            </button>
          </div>
          <p class="text-xs opacity-40 font-mono mt-1">
            {{ availableWebcams.length }} device{{ availableWebcams.length !== 1 ? 's' : '' }} found
          </p>
        </div>

        <!-- Name -->
        <div class="form-control mb-3">
          <label class="label py-1">
            <span class="label-text font-mono text-xs opacity-60">NAME</span>
          </label>
          <input v-model="form.name" type="text" placeholder="Front Door Cam"
            class="input input-bordered input-sm w-full font-mono"
            :class="{ 'input-error': formError }" />
        </div>

        <!-- Location (optional) -->
        <div class="form-control mb-3">
          <label class="label py-1">
            <span class="label-text font-mono text-xs opacity-60">LOCATION (OPTIONAL)</span>
          </label>
          <input v-model="form.location" type="text" placeholder="Lobby, Floor 1…"
            class="input input-bordered input-sm w-full font-mono" />
        </div>

        <!-- FPS -->
        <div class="form-control mb-4">
          <label class="label py-1">
            <span class="label-text font-mono text-xs opacity-60">FPS</span>
            <span class="label-text-alt font-mono text-xs opacity-60">{{ form.fps }}</span>
          </label>
          <input v-model.number="form.fps" type="range" min="1" max="30" step="1"
            class="range range-xs range-primary" />
          <div class="flex justify-between text-xs font-mono opacity-40 px-1">
            <span>1</span><span>15</span><span>30</span>
          </div>
        </div>

        <!-- Error -->
        <div v-if="formError" role="alert" class="alert alert-error text-xs font-mono p-2 mb-3">
          {{ formError }}
        </div>

        <!-- Actions -->
        <div class="modal-action mt-2">
          <button class="btn btn-ghost btn-sm font-mono" @click="closeAddWebcam">CANCEL</button>
          <button class="btn btn-primary btn-sm font-mono"
            :disabled="saving || form.device_index === null || !form.name.trim()"
            @click="submitWebcam">
            <span v-if="saving" class="loading loading-spinner loading-xs"></span>
            {{ saving ? 'ADDING…' : 'ADD CAMERA' }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- EDIT CAMERA MODAL                                                       -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <dialog ref="editModal" class="modal">
      <div class="modal-box max-w-sm">
        <h3 class="font-mono font-bold text-sm mb-4">EDIT CAMERA</h3>

        <div class="form-control mb-3">
          <label class="label py-1">
            <span class="label-text font-mono text-xs opacity-60">NAME</span>
          </label>
          <input v-model="editForm.name" type="text"
            class="input input-bordered input-sm w-full font-mono"
            :class="{ 'input-error': editError }" />
        </div>

        <div class="form-control mb-3">
          <label class="label py-1">
            <span class="label-text font-mono text-xs opacity-60">LOCATION (OPTIONAL)</span>
          </label>
          <input v-model="editForm.location" type="text" placeholder="Lobby, Floor 1…"
            class="input input-bordered input-sm w-full font-mono" />
        </div>

        <div class="form-control mb-4">
          <label class="label py-1">
            <span class="label-text font-mono text-xs opacity-60">FPS</span>
            <span class="label-text-alt font-mono text-xs opacity-60">{{ editForm.fps }}</span>
          </label>
          <input v-model.number="editForm.fps" type="range" min="1" max="30" step="1"
            class="range range-xs range-primary" />
          <div class="flex justify-between text-xs font-mono opacity-40 px-1">
            <span>1</span><span>15</span><span>30</span>
          </div>
        </div>

        <div v-if="editError" role="alert" class="alert alert-error text-xs font-mono p-2 mb-3">
          {{ editError }}
        </div>

        <div class="modal-action mt-2">
          <button class="btn btn-ghost btn-sm font-mono" @click="editModal?.close()">CANCEL</button>
          <button class="btn btn-primary btn-sm font-mono"
            :disabled="editSaving || !editForm.name.trim()"
            @click="submitEdit">
            <span v-if="editSaving" class="loading loading-spinner loading-xs"></span>
            {{ editSaving ? 'SAVING…' : 'SAVE' }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- DELETE CAMERA MODAL                                                     -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <dialog ref="deleteModal" class="modal">
      <div class="modal-box max-w-xs">
        <h3 class="font-mono font-bold text-sm mb-2">DELETE CAMERA</h3>
        <p class="text-sm opacity-70 mb-4">
          Delete <span class="font-semibold">{{ deleteCamTarget?.name }}</span>?
          This also removes all associated zones and cannot be undone.
        </p>
        <div v-if="deleteError" role="alert" class="alert alert-error text-xs font-mono p-2 mb-3">
          {{ deleteError }}
        </div>
        <div class="modal-action mt-2">
          <button class="btn btn-ghost btn-sm font-mono" @click="deleteModal?.close()">CANCEL</button>
          <button class="btn btn-error btn-sm font-mono"
            :disabled="deleteLoading"
            @click="submitDelete">
            <span v-if="deleteLoading" class="loading loading-spinner loading-xs"></span>
            {{ deleteLoading ? 'DELETING…' : 'DELETE' }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import { useCamerasStore } from '@/stores/cameras'
import { useAuthStore } from '@/stores/auth'
import { useEventsStore } from '@/stores/events'
import { useZonesStore } from '@/stores/zones'
import type { CameraRead, WebcamDevice } from '@/api/client'
import { parseUtcIso, fmtTime } from '@/utils/time'

const cameras = useCamerasStore()
const auth = useAuthStore()
const eventsStore = useEventsStore()
const zonesStore = useZonesStore()
const router = useRouter()
const layout = ref<'grid' | 'list'>('grid')
const filterState = ref('')
const showOverlays = ref(true)

// Timer to force re-evaluation of alert flashes
const now = ref(Date.now())
let flashTimer: ReturnType<typeof setInterval>

onMounted(async () => {
  cameras.fetchAll()
  zonesStore.fetchAll()
  flashTimer = setInterval(() => now.value = Date.now(), 500)
})

onUnmounted(() => {
  clearInterval(flashTimer)
})

// Build authenticated stream URL for MJPEG <img> tag
function streamUrl(cameraId: number): string {
  const token = localStorage.getItem('access_token') ?? ''
  return `/api/v1/cameras/${cameraId}/stream?token=${token}`
}

const filtered = computed(() =>
  cameras.cameras.filter(c =>
    !filterState.value || (cameras.statusOf(c.id)?.state ?? 'INACTIVE') === filterState.value
  )
)

const webcamCount = computed(() =>
  cameras.cameras.filter(c => c.source_type === 'webcam').length
)

function selectCam(id: number) {
  router.push({ path: '/pilot', query: { cam: id } })
}

// ── Overlays & Alert rendering ───────────────────────────────────────────────

function zonesByCamera(cameraId: number) {
  return zonesStore.zonesForCamera(cameraId)
}

function formatZonePoints(coords: string | [number, number][]) {
  try {
    const pts = typeof coords === 'string' ? JSON.parse(coords) as [number, number][] : coords
    return pts.map((p: any) => `${p[0] * 100},${p[1] * 100}`).join(' ')
  } catch {
    return ''
  }
}

function getZoneLabelPos(coords: string | [number, number][]): { x: number, y: number } {
  try {
    const pts = typeof coords === 'string' ? JSON.parse(coords) as [number, number][] : coords
    if (!pts || pts.length === 0) return { x: 0, y: 0 }
    // Find the point closest to top-left to place the label
    const topPt = pts.reduce((min: any, p: any) => (p[0]+p[1] < min[0]+min[1]) ? p : min, pts[0])
    return { x: topPt[0] * 100, y: topPt[1] * 100 }
  } catch {
    return { x: 0, y: 0 }
  }
}

function recentAlertFor(cameraId: number) {
  const currentMs = now.value
  const recent = eventsStore.events.find(e => e.camera_id === cameraId)
  if (!recent) return null
  const ageSecs = (currentMs - parseUtcIso(recent.occurred_at ?? '').getTime()) / 1000
  return ageSecs < 3.0 ? recent : null
}

function hasRecentAlert(cameraId: number): boolean {
  return recentAlertFor(cameraId) !== null
}

// ── Enable / Disable toggle ───────────────────────────────────────────────────

const toggling = ref<Set<number>>(new Set())

async function toggleCam(id: number, isActive: boolean) {
  toggling.value.add(id)
  try {
    await cameras.setActive(id, isActive)
  } finally {
    toggling.value.delete(id)
  }
}

// ── Edit Camera modal ─────────────────────────────────────────────────────────

const editModal = ref<HTMLDialogElement | null>(null)
const editSaving = ref(false)
const editError = ref('')
const editCamId = ref<number | null>(null)
const editForm = ref({ name: '', location: '', fps: 15 })

function openEditCam(cam: CameraRead) {
  editCamId.value = cam.id
  editForm.value = { name: cam.name, location: cam.location ?? '', fps: cam.fps ?? 15 }
  editError.value = ''
  editModal.value?.showModal()
}

async function submitEdit() {
  if (!editForm.value.name.trim()) { editError.value = 'Name is required'; return }
  editSaving.value = true
  editError.value = ''
  try {
    await cameras.updateCamera(editCamId.value!, {
      name: editForm.value.name.trim(),
      location: editForm.value.location.trim() || undefined,
      fps: editForm.value.fps,
    })
    editModal.value?.close()
  } catch (e: any) {
    editError.value = e.message ?? 'Failed to save'
  } finally {
    editSaving.value = false
  }
}

// ── Delete Camera modal ───────────────────────────────────────────────────────

const deleteModal = ref<HTMLDialogElement | null>(null)
const deleteLoading = ref(false)
const deleteError = ref('')
const deleteCamTarget = ref<CameraRead | null>(null)

function openDeleteCam(cam: CameraRead) {
  deleteCamTarget.value = cam
  deleteError.value = ''
  deleteModal.value?.showModal()
}

async function submitDelete() {
  if (!deleteCamTarget.value) return
  deleteLoading.value = true
  deleteError.value = ''
  try {
    await cameras.deleteCamera(deleteCamTarget.value.id)
    deleteModal.value?.close()
  } catch (e: any) {
    deleteError.value = e.message ?? 'Failed to delete'
  } finally {
    deleteLoading.value = false
  }
}

// ── Add Webcam modal ──────────────────────────────────────────────────────────

const webcamModal = ref<HTMLDialogElement | null>(null)
const probing = ref(false)
const saving = ref(false)
const availableWebcams = ref<WebcamDevice[]>([])
const formError = ref('')

const form = ref({
  name: '',
  location: '',
  device_index: null as number | null,
  device_name: null as string | null,
  fps: 15,
})

async function openAddWebcam() {
  formError.value = ''
  form.value = { name: '', location: '', device_index: null, device_name: null, fps: 15 }
  availableWebcams.value = []
  webcamModal.value?.showModal()
  probing.value = true
  try {
    availableWebcams.value = await cameras.listWebcams()
    if (availableWebcams.value.length === 1) {
      form.value.device_index = availableWebcams.value[0].index
      form.value.device_name = availableWebcams.value[0].device_name
    }
  } catch {
    formError.value = 'Failed to probe webcam devices'
  } finally {
    probing.value = false
  }
}

function closeAddWebcam() {
  webcamModal.value?.close()
}

async function submitWebcam() {
  formError.value = ''
  if (!form.value.name.trim()) { formError.value = 'Name is required'; return }
  if (form.value.device_index === null) { formError.value = 'Select a device'; return }

  saving.value = true
  try {
    await cameras.addCamera({
      source_type: 'webcam',
      name: form.value.name.trim(),
      location: form.value.location.trim() || undefined,
      device_index: form.value.device_index,
      device_name: form.value.device_name ?? undefined,
      fps: form.value.fps,
    })
    closeAddWebcam()
    await cameras.fetchAll()
  } catch (e: any) {
    formError.value = e.message ?? 'Failed to add camera'
  } finally {
    saving.value = false
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

// fmtTime imported from @/utils/time (parseUtcIso-based, UTC-correct)

function dotColor(state?: string) {
  return {
    ONLINE: 'bg-success animate-pulse', RECONNECTING: 'bg-warning animate-pulse',
    ERROR: 'bg-error', FAILED: 'bg-error', CONNECTING: 'bg-info animate-pulse',
    INACTIVE: 'bg-base-300',
  }[state ?? 'INACTIVE'] ?? 'bg-base-300'
}

function stateBadge(state?: string) {
  return {
    ONLINE: 'badge-success', RECONNECTING: 'badge-warning', ERROR: 'badge-error',
    FAILED: 'badge-error', CONNECTING: 'badge-info', INACTIVE: 'badge-ghost',
  }[state ?? 'INACTIVE'] ?? 'badge-ghost'
}

function cardBorder(state?: string) {
  return {
    ONLINE: 'border-success/30', RECONNECTING: 'border-warning/50',
    ERROR: 'border-error/60 glow-error', FAILED: 'border-error/60 glow-error',
    CONNECTING: 'border-info/30', INACTIVE: 'border-base-300',
  }[state ?? 'INACTIVE'] ?? 'border-base-300'
}
</script>
