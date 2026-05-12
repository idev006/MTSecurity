<template>
  <AppLayout>
    <div class="flex flex-col gap-4">

      <!-- ── Toolbar ──────────────────────────────────────────────────── -->
      <div class="flex items-center gap-3 flex-wrap">
        <h2 class="font-mono font-semibold tracking-wide text-sm">EVENTS & ALERTS</h2>
        <div class="badge font-mono text-xs"
          :class="events.newCount > 0 ? 'badge-error animate-pulse' : 'badge-ghost'">
          {{ events.newCount }} NEW
        </div>
        <div class="ml-auto flex items-center gap-2 flex-wrap">
          <select class="select select-xs select-bordered font-mono" v-model="filters.severity">
            <option value="">ALL SEV</option>
            <option value="critical">CRITICAL</option>
            <option value="high">HIGH</option>
            <option value="medium">MEDIUM</option>
            <option value="low">LOW</option>
          </select>
          <select class="select select-xs select-bordered font-mono" v-model="filters.status">
            <option value="">ALL STATUS</option>
            <option value="NEW">NEW</option>
            <option value="ACKNOWLEDGED">ACK</option>
            <option value="SILENCED">SILENCED</option>
            <option value="ESCALATED">ESCALATED</option>
          </select>
          <select class="select select-xs select-bordered font-mono" v-model="filters.behavior">
            <option value="">ALL TYPES</option>
            <option value="intrusion">INTRUSION</option>
            <option value="loitering">LOITERING</option>
            <option value="line_crossing">LINE CROSS</option>
            <option value="crowd_density">CROWD</option>
            <option value="abandoned_object">ABANDONED</option>
          </select>
          <button class="btn btn-xs btn-ghost font-mono" @click="load">↻ REFRESH</button>
        </div>
      </div>

      <!-- ── Bulk action bar ───────────────────────────────────────────── -->
      <div v-if="events.newCount > 0" class="alert alert-warning p-2 flex items-center gap-3">
        <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
        </svg>
        <span class="font-mono text-xs flex-1">
          {{ events.newCount }} UNACKNOWLEDGED ALERT{{ events.newCount !== 1 ? 'S' : '' }}
        </span>
        <button class="btn btn-xs btn-warning font-mono" @click="ackAll">ACK ALL</button>
      </div>

      <!-- ── Event table ───────────────────────────────────────────────── -->
      <div class="card bg-base-100 border border-base-300 shadow-none overflow-hidden">
        <div v-if="events.loading" class="flex justify-center py-12">
          <span class="loading loading-spinner loading-md opacity-40"></span>
        </div>

        <div v-else-if="filtered.length === 0"
          class="flex flex-col items-center py-16 opacity-30 gap-2">
          <svg class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1"
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <p class="font-mono text-sm">ALL CLEAR</p>
        </div>

        <div v-else class="overflow-x-auto">
          <table class="table table-sm">
            <thead>
              <tr class="font-mono text-xs opacity-50 border-b border-base-300">
                <th>TIME</th><th>CAM</th><th>TYPE</th><th>SEV</th>
                <th>CONF</th><th>STATUS</th><th>ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="ev in filtered" :key="ev.id"
                class="hover border-b border-base-300/30 last:border-0 transition-colors"
                :class="rowClass(ev.status)">
                <td class="font-mono text-xs whitespace-nowrap opacity-70">{{ fmtTime(ev.occurred_at) }}</td>
                <td class="text-xs"><span class="font-mono opacity-50">CAM</span> {{ ev.camera_id ?? '?' }}</td>
                <td class="text-xs capitalize font-semibold">{{ ev.behavior.replace(/_/g, ' ') }}</td>
                <td>
                  <span class="badge badge-xs font-mono" :class="sevClass(ev.severity)">
                    {{ ev.severity.toUpperCase() }}
                  </span>
                </td>
                <td class="font-mono text-xs">{{ (ev.confidence * 100).toFixed(0) }}%</td>
                <td>
                  <span class="badge badge-xs font-mono" :class="statusClass(ev.status)">{{ ev.status }}</span>
                  <span v-if="ev.acknowledged_by" class="text-xs opacity-40 ml-1">{{ ev.acknowledged_by }}</span>
                </td>
                <!-- Inline cockpit actions — no navigation required -->
                <td>
                  <div class="flex gap-1">
                    <a v-if="ev.snapshot_url" :href="`${ev.snapshot_url}?token=${auth.token}`" target="_blank"
                      class="btn btn-xs btn-ghost font-mono" title="Snapshot">📷</a>
                    <button v-if="ev.status === 'NEW'"
                      class="btn btn-xs btn-success font-mono"
                      :disabled="busy.has(ev.id)" @click="ack(ev.id)">ACK</button>
                    <button v-if="ev.status === 'NEW' || ev.status === 'ESCALATED'"
                      class="btn btn-xs btn-warning font-mono"
                      :disabled="busy.has(ev.id)" @click="silence(ev.id)">5MIN</button>
                    <button v-if="ev.status === 'NEW'"
                      class="btn btn-xs btn-error font-mono"
                      :disabled="busy.has(ev.id)" @click="escalate(ev.id)">↑↑</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination -->
        <div class="flex items-center justify-between px-4 py-2 border-t border-base-300 text-xs font-mono opacity-60">
          <span>{{ filtered.length }} EVENTS</span>
          <div class="join">
            <button class="btn btn-xs join-item btn-ghost font-mono"
              :disabled="page <= 1" @click="page--; load()">← PREV</button>
            <button class="btn btn-xs join-item btn-ghost font-mono pointer-events-none">{{ page }}</button>
            <button class="btn btn-xs join-item btn-ghost font-mono"
              :disabled="events.events.length < pageSize" @click="page++; load()">NEXT →</button>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import { useEventsStore } from '@/stores/events'
import { useAuthStore } from '@/stores/auth'

const events = useEventsStore()
const auth = useAuthStore()
const page = ref(1)
const pageSize = 50
const filters = ref({ severity: '', status: '', behavior: '' })

watch(filters, () => { page.value = 1; load() }, { deep: true })
onMounted(() => load())

async function load() {
  const params: Record<string, string | number> = { page: page.value, page_size: pageSize }
  if (filters.value.severity) params.severity = filters.value.severity
  if (filters.value.status)   params.status   = filters.value.status
  await events.fetchRecent(params)
}

const filtered = computed(() =>
  events.events.filter(e => !filters.value.behavior || e.behavior === filters.value.behavior)
)

const busy = ref<Set<number>>(new Set())

async function ack(id: number) {
  busy.value.add(id)
  try { await events.acknowledge(id) } finally { busy.value.delete(id) }
}
async function silence(id: number) {
  busy.value.add(id)
  try { await events.silence(id, 300) } finally { busy.value.delete(id) }
}
async function escalate(id: number) {
  busy.value.add(id)
  try { await events.escalate(id, 'Escalated from console') } finally { busy.value.delete(id) }
}
async function ackAll() {
  await Promise.allSettled(
    events.events.filter(e => e.status === 'NEW').map(e => events.acknowledge(e.id))
  )
}

function fmtTime(iso: string) {
  return new Date(iso).toLocaleString([], {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}
function rowClass(s: string) {
  return {
    'bg-error/5 border-l-2 border-l-error': s === 'NEW',
    'bg-warning/5 border-l-2 border-l-warning': s === 'ESCALATED',
    'opacity-50': s === 'SILENCED',
  }
}
function sevClass(s: string) {
  return { critical: 'badge-error', high: 'badge-warning', medium: 'badge-info', low: 'badge-ghost' }[s] ?? 'badge-ghost'
}
function statusClass(s: string) {
  return { NEW: 'badge-error', ACKNOWLEDGED: 'badge-success', SILENCED: 'badge-ghost', ESCALATED: 'badge-warning' }[s] ?? 'badge-ghost'
}
</script>
