<template>
  <AppLayout>
    <div class="flex flex-col gap-4">

      <!-- ── Instrument Cluster ────────────────────────────────────────── -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">

        <!-- Cameras Online -->
        <div class="stat bg-base-100 rounded-xl border border-base-300 py-3 px-4 stat-card-hover">
          <div class="stat-figure text-primary opacity-60">
            <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
          </div>
          <div class="stat-title font-mono text-xs tracking-widest opacity-50">CAMERAS</div>
          <div class="stat-value font-mono text-3xl leading-tight"
            :class="cameras.failed > 0 ? 'text-warning' : 'text-success'">
            {{ cameras.online }}<span class="text-lg opacity-40">/{{ cameras.total }}</span>
          </div>
          <div class="stat-desc font-mono text-xs mt-0.5">
            <span v-if="cameras.reconnecting > 0" class="text-warning">{{ cameras.reconnecting }} RECONN </span>
            <span v-if="cameras.failed > 0" class="text-error">{{ cameras.failed }} ERR</span>
            <span v-if="cameras.reconnecting === 0 && cameras.failed === 0" class="text-success">ALL ONLINE</span>
          </div>
        </div>

        <!-- Active Alerts -->
        <div class="stat bg-base-100 rounded-xl border py-3 px-4 stat-card-hover transition-shadow duration-300"
          :class="events.newCount > 0 ? ['border-error/50', 'glow-error'] : 'border-base-300'">
          <div class="stat-figure opacity-60" :class="events.newCount > 0 ? 'text-error' : 'text-success'">
            <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
            </svg>
          </div>
          <div class="stat-title font-mono text-xs tracking-widest opacity-50">ALERTS</div>
          <div class="stat-value font-mono text-3xl leading-tight"
            :class="events.newCount > 0 ? 'text-error' : 'text-success'">
            {{ events.newCount }}
          </div>
          <div class="stat-desc font-mono text-xs mt-0.5">
            <span v-if="events.newCount > 0" class="text-error animate-pulse">REQUIRES ATTENTION</span>
            <span v-else class="text-success">NOMINAL</span>
          </div>
        </div>

        <!-- CPU Load -->
        <div class="stat bg-base-100 rounded-xl border border-base-300 py-3 px-4 stat-card-hover">
          <div class="stat-figure opacity-60" :class="gaugeColor(system.cpuPercent)">
            <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M9 3H7a2 2 0 00-2 2v2M9 3h6M9 3v2m6-2h2a2 2 0 012 2v2M15 3v2M3 9h2m14 0h2M3 15h2m14 0h2M9 21H7a2 2 0 01-2-2v-2m4 4h6m-6 0v-2m6 2h2a2 2 0 002-2v-2m-4 4v-2M9 9h6v6H9z"/>
            </svg>
          </div>
          <div class="stat-title font-mono text-xs tracking-widest opacity-50">CPU LOAD</div>
          <div class="stat-value font-mono text-3xl leading-tight" :class="gaugeColor(system.cpuPercent)">
            {{ system.cpuPercent.toFixed(0) }}<span class="text-lg opacity-40">%</span>
          </div>
          <div class="w-full mt-1.5">
            <progress class="progress progress-xs w-full" :class="progressClass(system.cpuPercent)"
              :value="system.cpuPercent" max="100"></progress>
          </div>
        </div>

        <!-- RAM Usage -->
        <div class="stat bg-base-100 rounded-xl border border-base-300 py-3 px-4 stat-card-hover">
          <div class="stat-figure opacity-60" :class="gaugeColor(system.ramPercent)">
            <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                d="M4 7v10M8 7v10M12 7v10M16 7v10M20 7v10M2 9h20M2 15h20"/>
            </svg>
          </div>
          <div class="stat-title font-mono text-xs tracking-widest opacity-50">RAM USAGE</div>
          <div class="stat-value font-mono text-3xl leading-tight" :class="gaugeColor(system.ramPercent)">
            {{ system.ramPercent.toFixed(0) }}<span class="text-lg opacity-40">%</span>
          </div>
          <div class="w-full mt-1.5">
            <progress class="progress progress-xs w-full" :class="progressClass(system.ramPercent)"
              :value="system.ramPercent" max="100"></progress>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">

        <!-- ── Recent Alerts ───────────────────────────────────────────── -->
        <div class="lg:col-span-2 card bg-base-100 border border-base-300 shadow-none">
          <div class="card-body p-0">

            <!-- Header -->
            <div class="flex items-center justify-between px-4 py-2.5 border-b border-base-300">
              <div class="flex items-center gap-2">
                <svg class="h-3.5 w-3.5 text-primary opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
                <h2 class="font-mono text-xs font-bold tracking-widest opacity-60">RECENT ALERTS</h2>
              </div>
              <div class="flex items-center gap-2">
                <span v-if="events.loading" class="loading loading-spinner loading-xs opacity-30"></span>
                <RouterLink to="/events" class="btn btn-ghost btn-xs font-mono opacity-60 hover:opacity-100">
                  VIEW ALL →
                </RouterLink>
              </div>
            </div>

            <!-- Empty state -->
            <div v-if="events.recentAlerts.length === 0 && !events.loading"
              class="flex flex-col items-center justify-center py-12 gap-2 opacity-25">
              <svg class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.2"
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <p class="font-mono text-xs tracking-widest">ALL CLEAR — NO RECENT ALERTS</p>
            </div>

            <!-- Table -->
            <div v-else class="overflow-x-auto">
              <table class="w-full text-[11px] font-mono">
                <thead>
                  <tr class="border-b border-base-300">
                    <th class="px-4 py-1.5 text-left font-normal opacity-40 tracking-widest">TIME</th>
                    <th class="px-2 py-1.5 text-left font-normal opacity-40 tracking-widest">CAM</th>
                    <th class="px-2 py-1.5 text-left font-normal opacity-40 tracking-widest">TYPE</th>
                    <th class="px-2 py-1.5 text-left font-normal opacity-40 tracking-widest">SEV</th>
                    <th class="px-2 py-1.5 text-left font-normal opacity-40 tracking-widest">STATUS</th>
                    <th class="px-2 py-1.5"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="ev in events.recentAlerts" :key="ev.id"
                    class="group border-b border-base-300/40 hover:bg-base-200/30 transition-colors"
                    :class="ev.status === 'NEW' ? 'row-new' : ''">
                    <td class="px-4 py-1 opacity-50 whitespace-nowrap" :title="ev.occurred_at">
                      {{ relTime(ev.occurred_at) }}
                    </td>
                    <td class="px-2 py-1 opacity-70">{{ ev.camera_id ?? '—' }}</td>
                    <td class="px-2 py-1 font-semibold capitalize">
                      {{ ev.behavior.replace(/_/g, ' ') }}
                    </td>
                    <td class="px-2 py-1">
                      <span class="badge badge-xs font-mono" :class="sevClass(ev.severity)">
                        {{ ev.severity.slice(0,4).toUpperCase() }}
                      </span>
                    </td>
                    <td class="px-2 py-1">
                      <span class="badge badge-xs font-mono" :class="statusClass(ev.status)">
                        {{ ev.status }}
                      </span>
                    </td>
                    <td class="px-2 py-1 text-right">
                      <button v-if="ev.status === 'NEW'"
                        class="btn btn-xs btn-square btn-success btn-outline action-reveal"
                        :class="{ 'opacity-100': acking.has(ev.id) }"
                        :disabled="acking.has(ev.id)"
                        title="Acknowledge"
                        @click="ack(ev.id)">
                        <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                        </svg>
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- ── Camera Status ───────────────────────────────────────────── -->
        <div class="card bg-base-100 border border-base-300 shadow-none">
          <div class="card-body p-0">

            <!-- Header -->
            <div class="flex items-center justify-between px-4 py-2.5 border-b border-base-300">
              <div class="flex items-center gap-2">
                <svg class="h-3.5 w-3.5 text-primary opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                </svg>
                <h2 class="font-mono text-xs font-bold tracking-widest opacity-60">CAMERA STATUS</h2>
              </div>
              <RouterLink to="/cameras" class="btn btn-ghost btn-xs font-mono opacity-60 hover:opacity-100">GRID →</RouterLink>
            </div>

            <div v-if="cameras.loading" class="flex justify-center py-10">
              <span class="loading loading-spinner loading-sm opacity-30"></span>
            </div>

            <div v-else-if="cameras.cameras.length === 0"
              class="flex justify-center py-10 opacity-25">
              <p class="font-mono text-xs">NO CAMERAS CONFIGURED</p>
            </div>

            <div v-else class="divide-y divide-base-300">
              <div v-for="cam in cameras.cameras" :key="cam.id"
                class="flex items-center gap-3 px-4 py-2.5 hover:bg-base-200/40 transition-colors"
                :class="cameras.statusOf(cam.id)?.state === 'ONLINE' ? 'border-l-2 border-success' :
                        cameras.statusOf(cam.id)?.state === 'ERROR'  ? 'border-l-2 border-error' :
                        cameras.statusOf(cam.id)?.state === 'RECONNECTING' ? 'border-l-2 border-warning' :
                        'border-l-2 border-transparent'">

                <span class="w-2 h-2 rounded-full shrink-0 mt-0.5"
                  :class="dotColor(cameras.statusOf(cam.id)?.state)"></span>

                <div class="flex-1 min-w-0">
                  <p class="text-xs font-semibold truncate"
                    :class="cameras.statusOf(cam.id)?.state === 'INACTIVE' ? 'opacity-40' : ''">
                    {{ cam.name }}
                  </p>
                  <!-- FPS mini bar -->
                  <div v-if="cameras.statusOf(cam.id)?.fps"
                    class="flex items-center gap-1.5 mt-0.5">
                    <progress class="progress progress-xs w-14 opacity-50"
                      :class="progressClass((cameras.statusOf(cam.id)?.fps ?? 0) / 30 * 100)"
                      :value="cameras.statusOf(cam.id)?.fps ?? 0" max="30"></progress>
                    <span class="font-mono text-[10px] opacity-40">
                      {{ cameras.statusOf(cam.id)?.fps?.toFixed(0) }}fps
                    </span>
                  </div>
                </div>

                <span class="badge badge-xs font-mono shrink-0"
                  :class="stateBadge(cameras.statusOf(cam.id)?.state)">
                  {{ cameras.statusOf(cam.id)?.state ?? 'INACTIVE' }}
                </span>
              </div>
            </div>

            <!-- Footer link -->
            <div class="px-4 py-2 border-t border-base-300">
              <RouterLink to="/events" class="btn btn-xs btn-ghost w-full font-mono opacity-50">
                VIEW ALERT LOG →
              </RouterLink>
            </div>
          </div>
        </div>

      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import { useCamerasStore } from '@/stores/cameras'
import { useEventsStore } from '@/stores/events'
import { useSystemStore } from '@/stores/system'
import { relTime, fmtTime } from '@/utils/time'

const cameras = useCamerasStore()
const events  = useEventsStore()
const system  = useSystemStore()

const acking = ref<Set<number>>(new Set())

async function ack(id: number) {
  acking.value.add(id)
  try { await events.acknowledge(id) }
  finally { acking.value.delete(id) }
}

// relTime + fmtTime imported from @/utils/time (parseUtcIso-based, UTC-correct)

// ── Colors ────────────────────────────────────────────────────────────────
function gaugeColor(pct: number) {
  if (pct >= 90) return 'text-error'
  if (pct >= 70) return 'text-warning'
  return 'text-base-content'
}

function progressClass(pct: number) {
  if (pct >= 90) return 'progress-error'
  if (pct >= 70) return 'progress-warning'
  return 'progress-success'
}

function sevClass(s: string) {
  return { critical: 'badge-error', high: 'badge-warning', medium: 'badge-info', low: 'badge-ghost' }[s] ?? 'badge-ghost'
}

function rowSevClass(s: string) {
  return { critical: 'row-critical', high: 'row-high', medium: 'row-medium', low: 'row-low' }[s] ?? ''
}

function statusClass(s: string) {
  return {
    NEW: 'badge-error', ACKNOWLEDGED: 'badge-success',
    SILENCED: 'badge-ghost', ESCALATED: 'badge-warning',
  }[s] ?? 'badge-ghost'
}

function dotColor(state?: string) {
  return {
    ONLINE: 'bg-success animate-pulse', RECONNECTING: 'bg-warning animate-pulse',
    ERROR: 'bg-error', FAILED: 'bg-error',
    CONNECTING: 'bg-info animate-pulse', INACTIVE: 'bg-base-300',
  }[state ?? 'INACTIVE'] ?? 'bg-base-300'
}

function stateBadge(state?: string) {
  return {
    ONLINE: 'badge-success', RECONNECTING: 'badge-warning',
    ERROR: 'badge-error', FAILED: 'badge-error',
    CONNECTING: 'badge-info', INACTIVE: 'badge-ghost',
  }[state ?? 'INACTIVE'] ?? 'badge-ghost'
}
</script>
