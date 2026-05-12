<template>
  <AppLayout>
    <div class="flex flex-col gap-4">

      <!-- ── Instrument cluster (top row) ──────────────────────────────── -->
      <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">

        <!-- Cameras online -->
        <div class="stat bg-base-100 rounded-box border border-base-300 py-3 px-4">
          <div class="stat-title text-xs font-mono opacity-60">CAMERAS ONLINE</div>
          <div class="stat-value text-2xl font-mono" :class="cameras.failed > 0 ? 'text-warning' : 'text-success'">
            {{ cameras.online }}<span class="text-base opacity-40">/{{ cameras.total }}</span>
          </div>
          <div class="stat-desc text-xs font-mono">
            <span v-if="cameras.reconnecting > 0" class="text-warning">{{ cameras.reconnecting }} RECONN</span>
            <span v-if="cameras.failed > 0" class="text-error ml-1">{{ cameras.failed }} ERR</span>
            <span v-if="cameras.reconnecting === 0 && cameras.failed === 0" class="text-success">ALL CLEAR</span>
          </div>
        </div>

        <!-- Active alerts -->
        <div class="stat bg-base-100 rounded-box border py-3 px-4"
          :class="events.newCount > 0 ? 'border-error' : 'border-base-300'">
          <div class="stat-title text-xs font-mono opacity-60">ACTIVE ALERTS</div>
          <div class="stat-value text-2xl font-mono" :class="events.newCount > 0 ? 'text-error' : 'text-success'">
            {{ events.newCount }}
          </div>
          <div class="stat-desc text-xs font-mono">
            <span v-if="events.newCount > 0" class="text-error animate-pulse">REQUIRES ATTENTION</span>
            <span v-else class="text-success">NOMINAL</span>
          </div>
        </div>

        <!-- CPU -->
        <div class="stat bg-base-100 rounded-box border border-base-300 py-3 px-4">
          <div class="stat-title text-xs font-mono opacity-60">CPU LOAD</div>
          <div class="stat-value text-2xl font-mono" :class="gaugeColor(system.cpuPercent)">
            {{ system.cpuPercent.toFixed(0) }}<span class="text-base opacity-40">%</span>
          </div>
          <div class="w-full mt-1">
            <progress class="progress progress-xs w-full"
              :class="progressClass(system.cpuPercent)"
              :value="system.cpuPercent" max="100"></progress>
          </div>
        </div>

        <!-- RAM -->
        <div class="stat bg-base-100 rounded-box border border-base-300 py-3 px-4">
          <div class="stat-title text-xs font-mono opacity-60">RAM USAGE</div>
          <div class="stat-value text-2xl font-mono" :class="gaugeColor(system.ramPercent)">
            {{ system.ramPercent.toFixed(0) }}<span class="text-base opacity-40">%</span>
          </div>
          <div class="w-full mt-1">
            <progress class="progress progress-xs w-full"
              :class="progressClass(system.ramPercent)"
              :value="system.ramPercent" max="100"></progress>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">

        <!-- ── Recent alerts panel ─────────────────────────────────────── -->
        <div class="lg:col-span-2 card bg-base-100 border border-base-300 shadow-none">
          <div class="card-body p-0">
            <div class="flex items-center justify-between px-4 py-2 border-b border-base-300">
              <h2 class="font-semibold text-sm tracking-wide font-mono">RECENT ALERTS</h2>
              <div class="flex gap-2 items-center">
                <span v-if="events.loading" class="loading loading-spinner loading-xs opacity-40"></span>
                <RouterLink to="/events" class="btn btn-ghost btn-xs font-mono">VIEW ALL →</RouterLink>
              </div>
            </div>

            <!-- Empty state -->
            <div v-if="events.recentAlerts.length === 0 && !events.loading"
              class="flex flex-col items-center justify-center py-10 opacity-30">
              <svg class="h-8 w-8 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <p class="text-xs font-mono">NO ALERTS</p>
            </div>

            <div v-else class="overflow-x-auto">
              <table class="table table-xs">
                <thead>
                  <tr class="font-mono text-xs opacity-50">
                    <th>TIME</th><th>CAM</th><th>TYPE</th><th>SEV</th><th>STATUS</th><th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="ev in events.recentAlerts" :key="ev.id"
                    class="hover" :class="ev.status === 'NEW' ? 'bg-error/5' : ''">
                    <td class="font-mono text-xs opacity-60">{{ fmtTime(ev.occurred_at) }}</td>
                    <td class="text-xs">{{ ev.camera_id ?? '—' }}</td>
                    <td class="text-xs capitalize">{{ ev.behavior.replace('_', ' ') }}</td>
                    <td>
                      <span class="badge badge-xs font-mono" :class="sevClass(ev.severity)">
                        {{ ev.severity.toUpperCase() }}
                      </span>
                    </td>
                    <td>
                      <span class="badge badge-xs font-mono" :class="statusClass(ev.status)">
                        {{ ev.status }}
                      </span>
                    </td>
                    <td>
                      <button v-if="ev.status === 'NEW'"
                        class="btn btn-xs btn-ghost font-mono"
                        :disabled="acking.has(ev.id)"
                        @click="ack(ev.id)">
                        ACK
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- ── Camera status panel ────────────────────────────────────── -->
        <div class="card bg-base-100 border border-base-300 shadow-none">
          <div class="card-body p-0">
            <div class="flex items-center justify-between px-4 py-2 border-b border-base-300">
              <h2 class="font-semibold text-sm tracking-wide font-mono">CAMERA STATUS</h2>
              <RouterLink to="/cameras" class="btn btn-ghost btn-xs font-mono">GRID →</RouterLink>
            </div>

            <div v-if="cameras.loading" class="flex justify-center py-8">
              <span class="loading loading-spinner loading-sm opacity-40"></span>
            </div>

            <div v-else class="divide-y divide-base-300">
              <div v-for="cam in cameras.cameras" :key="cam.id"
                class="flex items-center justify-between px-4 py-2 hover:bg-base-200/50 transition-colors">
                <div class="flex items-center gap-2 min-w-0">
                  <span class="inline-block w-2 h-2 rounded-full shrink-0"
                    :class="dotColor(cameras.statusOf(cam.id)?.state)"></span>
                  <span class="text-xs truncate">{{ cam.name }}</span>
                </div>
                <div class="flex items-center gap-2 shrink-0">
                  <span v-if="cameras.statusOf(cam.id)?.fps"
                    class="text-xs font-mono opacity-50">
                    {{ cameras.statusOf(cam.id)?.fps?.toFixed(0) }}fps
                  </span>
                  <span class="badge badge-xs font-mono"
                    :class="stateBadge(cameras.statusOf(cam.id)?.state)">
                    {{ cameras.statusOf(cam.id)?.state ?? 'INACTIVE' }}
                  </span>
                </div>
              </div>

              <div v-if="cameras.cameras.length === 0"
                class="flex justify-center py-8 opacity-30">
                <p class="text-xs font-mono">NO CAMERAS CONFIGURED</p>
              </div>
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

const cameras = useCamerasStore()
const events  = useEventsStore()
const system  = useSystemStore()

const acking = ref<Set<number>>(new Set())

async function ack(id: number) {
  acking.value.add(id)
  try { await events.acknowledge(id) }
  finally { acking.value.delete(id) }
}

// ── Formatting ────────────────────────────────────────────────────────────
function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

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
  return {
    critical: 'badge-error',
    high:     'badge-warning',
    medium:   'badge-info',
    low:      'badge-ghost',
  }[s] ?? 'badge-ghost'
}

function statusClass(s: string) {
  return {
    NEW:          'badge-error',
    ACKNOWLEDGED: 'badge-success',
    SILENCED:     'badge-ghost',
    ESCALATED:    'badge-warning',
  }[s] ?? 'badge-ghost'
}

function dotColor(state?: string) {
  return {
    ONLINE:       'bg-success animate-pulse',
    RECONNECTING: 'bg-warning animate-pulse',
    ERROR:        'bg-error',
    FAILED:       'bg-error',
    CONNECTING:   'bg-info animate-pulse',
    INACTIVE:     'bg-base-300',
  }[state ?? 'INACTIVE'] ?? 'bg-base-300'
}

function stateBadge(state?: string) {
  return {
    ONLINE:       'badge-success',
    RECONNECTING: 'badge-warning',
    ERROR:        'badge-error',
    FAILED:       'badge-error',
    CONNECTING:   'badge-info',
    INACTIVE:     'badge-ghost',
  }[state ?? 'INACTIVE'] ?? 'badge-ghost'
}
</script>
