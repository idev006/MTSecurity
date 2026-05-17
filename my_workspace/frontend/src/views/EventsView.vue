<template>
  <AppLayout>
    <div class="flex flex-col gap-3">

      <!-- ── Toolbar ─────────────────────────────────────────────────────── -->
      <div class="flex items-center gap-2 flex-wrap">
        <div class="flex items-center gap-2">
          <svg class="h-3.5 w-3.5 text-primary opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
          <h2 class="font-mono text-xs font-bold tracking-widest opacity-60">EVENTS & ALERTS</h2>
          <span class="badge badge-xs font-mono"
            :class="newCount > 0 ? 'badge-error animate-pulse' : 'badge-ghost'">
            {{ newCount }} NEW
          </span>
        </div>

        <!-- Filters -->
        <div class="ml-auto flex items-center gap-1.5 flex-wrap">
          <div class="join">
            <select class="join-item select select-xs select-bordered font-mono"
              v-model="severity" @change="resetAndLoad">
              <option value="">ALL SEV</option>
              <option value="critical">CRITICAL</option>
              <option value="high">HIGH</option>
              <option value="medium">MEDIUM</option>
              <option value="low">LOW</option>
            </select>
            <select class="join-item select select-xs select-bordered font-mono"
              v-model="status" @change="resetAndLoad">
              <option value="">ALL STATUS</option>
              <option value="NEW">NEW</option>
              <option value="ACKNOWLEDGED">ACK</option>
              <option value="SILENCED">SILENCED</option>
              <option value="ESCALATED">ESCALATED</option>
            </select>
            <select class="join-item select select-xs select-bordered font-mono"
              v-model="behavior" @change="resetAndLoad">
              <option value="">ALL TYPES</option>
              <option value="intrusion">INTRUSION</option>
              <option value="loitering">LOITERING</option>
              <option value="line_crossing">LINE CROSS</option>
              <option value="crowd_density">CROWD</option>
              <option value="abandoned_object">ABANDONED</option>
            </select>
          </div>
          <div class="tooltip tooltip-left" data-tip="Refresh">
            <button class="btn btn-square btn-xs btn-ghost opacity-60 hover:opacity-100" @click="load">
              <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- ── Bulk action bar ──────────────────────────────────────────────── -->
      <div v-if="newCount > 0"
        class="flex items-center gap-3 px-3 py-2 rounded-lg bg-error/10 border border-error/30 backdrop-blur-sm glow-error">
        <svg class="h-4 w-4 shrink-0 text-error" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
        </svg>
        <span class="font-mono text-xs flex-1 text-error font-semibold">
          {{ newCount }} UNACKNOWLEDGED ALERT{{ newCount !== 1 ? 'S' : '' }}
        </span>
        <button class="btn btn-xs btn-error btn-outline font-mono" @click="ackAll">ACK ALL</button>
      </div>

      <!-- ── Event table ──────────────────────────────────────────────────── -->
      <div class="card bg-base-100 border border-base-300 shadow-none overflow-hidden">

        <!-- Card header -->
        <div class="flex items-center justify-between px-4 py-2.5 border-b border-base-300">
          <span class="font-mono text-xs opacity-40">{{ total.toLocaleString() }} EVENTS</span>
          <span v-if="loading" class="loading loading-spinner loading-xs opacity-30"></span>
        </div>

        <div v-if="loading && rows.length === 0" class="flex justify-center py-12">
          <span class="loading loading-spinner loading-md opacity-30"></span>
        </div>

        <div v-else-if="rows.length === 0"
          class="flex flex-col items-center py-16 gap-2 opacity-25">
          <svg class="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1"
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <p class="font-mono text-sm tracking-widest">ALL CLEAR</p>
          <p class="font-mono text-xs">No events match the current filters</p>
        </div>

        <div v-else class="overflow-x-auto">
          <table class="table table-sm table-pin-rows">
            <thead>
              <tr class="font-mono text-xs opacity-40 border-b border-base-300">
                <th class="pl-4 w-4"></th>
                <th>TIME</th><th>CAM</th><th>TYPE</th>
                <th>SEV</th><th>CONF</th><th>STATUS</th><th class="text-right pr-3">ACTIONS</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="ev in rows" :key="ev.id"
                class="border-b border-base-300/20 last:border-0 transition-colors"
                :class="[rowClass(ev), 'hover']">
                <!-- Severity strip -->
                <td class="p-0 w-1">
                  <div class="w-1 h-full min-h-[2.5rem]" :class="sevStripClass(ev.severity)"></div>
                </td>
                <td class="font-mono text-xs whitespace-nowrap opacity-60" :title="ev.occurred_at">
                  {{ relTime(ev.occurred_at) }}
                </td>
                <td class="font-mono text-xs opacity-60">{{ ev.camera_id ?? '?' }}</td>
                <td class="text-xs font-semibold capitalize">{{ ev.behavior.replace(/_/g, ' ') }}</td>
                <td>
                  <span class="badge badge-xs font-mono" :class="sevClass(ev.severity)">
                    {{ ev.severity.slice(0,4).toUpperCase() }}
                  </span>
                </td>
                <td>
                  <span class="badge badge-xs badge-ghost font-mono">
                    {{ (ev.confidence * 100).toFixed(0) }}%
                  </span>
                </td>
                <td>
                  <div>
                    <span class="badge badge-xs font-mono" :class="statusClass(ev.status)">{{ ev.status }}</span>
                    <span v-if="ev.acknowledged_by" class="block text-[10px] opacity-30 font-mono mt-0.5">
                      {{ ev.acknowledged_by }}
                    </span>
                  </div>
                </td>
                <!-- Always-visible action buttons -->
                <td class="text-right pr-2">
                  <div class="flex gap-1 justify-end">
                    <div v-if="ev.snapshot_url" class="tooltip tooltip-left" data-tip="View snapshot">
                      <button class="btn btn-xs btn-square btn-ghost" @click="openSnapshot(ev)">
                        <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/>
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"/>
                        </svg>
                      </button>
                    </div>
                    <div class="tooltip tooltip-left" :data-tip="ev.status === 'NEW' ? 'Acknowledge' : 'Already acknowledged'">
                      <button class="btn btn-xs btn-square"
                        :class="ev.status === 'NEW' ? 'btn-success btn-outline' : 'btn-ghost opacity-20'"
                        :disabled="busy.has(ev.id) || ev.status !== 'NEW'"
                        @click="ev.status === 'NEW' && ack(ev)">
                        <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                        </svg>
                      </button>
                    </div>
                    <div class="tooltip tooltip-left" data-tip="Silence 5 min">
                      <button class="btn btn-xs btn-square"
                        :class="(ev.status === 'NEW' || ev.status === 'ESCALATED') ? 'btn-warning btn-outline' : 'btn-ghost opacity-20'"
                        :disabled="busy.has(ev.id) || (ev.status !== 'NEW' && ev.status !== 'ESCALATED')"
                        @click="(ev.status === 'NEW' || ev.status === 'ESCALATED') && silence(ev)">
                        <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z"/>
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2"/>
                        </svg>
                      </button>
                    </div>
                    <div class="tooltip tooltip-left" data-tip="Escalate">
                      <button class="btn btn-xs btn-square"
                        :class="ev.status === 'NEW' ? 'btn-error btn-outline' : 'btn-ghost opacity-20'"
                        :disabled="busy.has(ev.id) || ev.status !== 'NEW'"
                        @click="ev.status === 'NEW' && escalate(ev)">
                        <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 15l7-7 7 7"/>
                        </svg>
                      </button>
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Pagination footer -->
        <div class="flex items-center justify-between px-4 py-2 border-t border-base-300 flex-wrap gap-2">
          <!-- Page size selector -->
          <div class="flex items-center gap-2">
            <span class="font-mono text-xs opacity-40">ROWS</span>
            <div class="join">
              <button v-for="s in PAGE_SIZES" :key="s"
                class="join-item btn btn-xs font-mono"
                :class="pageSize === s ? 'btn-neutral' : 'btn-ghost'"
                @click="onPageSizeClick(s)">
                {{ s }}
              </button>
            </div>
          </div>

          <!-- Page navigation -->
          <div class="join">
            <button class="join-item btn btn-xs btn-ghost font-mono"
              :disabled="page <= 1" @click="prevPage">← PREV</button>
            <button class="join-item btn btn-xs btn-ghost font-mono pointer-events-none opacity-60">
              PAGE {{ page }} / {{ Math.max(1, Math.ceil(total / pageSize)) }}
            </button>
            <button class="join-item btn btn-xs btn-ghost font-mono"
              :disabled="!hasNextPage" @click="nextPage">NEXT →</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <!-- SNAPSHOT MODAL                                                          -->
    <!-- ══════════════════════════════════════════════════════════════════════ -->
    <dialog ref="snapshotModal" class="modal">
      <div class="modal-box max-w-3xl p-0 overflow-hidden">
        <!-- Header -->
        <div class="flex items-center justify-between px-4 py-3 border-b border-base-300 bg-base-200">
          <div class="flex items-center gap-3">
            <span class="badge badge-sm font-mono" :class="sevClass(snapshotEv?.severity ?? '')">
              {{ (snapshotEv?.severity ?? '').toUpperCase() }}
            </span>
            <span class="font-mono text-xs font-bold tracking-wider capitalize">
              {{ snapshotEv?.behavior.replace(/_/g, ' ') }}
            </span>
            <span class="font-mono text-xs opacity-50">
              CAM {{ snapshotEv?.camera_id }} · {{ snapshotEv ? relTime(snapshotEv.occurred_at) : '' }}
            </span>
          </div>
          <div class="flex items-center gap-2">
            <!-- Open in new tab -->
            <a v-if="snapshotEv?.snapshot_url"
              :href="`${snapshotEv.snapshot_url}?token=${token}`"
              target="_blank"
              class="btn btn-xs btn-ghost font-mono gap-1 opacity-60 hover:opacity-100">
              <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
              </svg>
              OPEN
            </a>
            <button class="btn btn-xs btn-square btn-ghost opacity-60 hover:opacity-100"
              @click="snapshotModal?.close()">
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- Image -->
        <div class="bg-black flex items-center justify-center min-h-48">
          <img v-if="snapshotEv?.snapshot_url"
            :src="`${snapshotEv.snapshot_url}?token=${token}`"
            class="max-w-full max-h-[70vh] object-contain"
            alt="Event snapshot" />
          <span v-else class="opacity-30 font-mono text-xs">NO IMAGE</span>
        </div>

        <!-- Footer metadata -->
        <div class="px-4 py-2.5 border-t border-base-300 bg-base-200 flex items-center gap-4 flex-wrap">
          <span class="font-mono text-xs opacity-50">
            CONF {{ snapshotEv ? (snapshotEv.confidence * 100).toFixed(0) + '%' : '—' }}
          </span>
          <span class="font-mono text-xs opacity-50">
            STATUS
            <span class="font-bold" :class="statusClass(snapshotEv?.status ?? '')">
              {{ snapshotEv?.status }}
            </span>
          </span>
          <span v-if="snapshotEv?.acknowledged_by" class="font-mono text-xs opacity-50">
            ACK BY {{ snapshotEv.acknowledged_by }}
          </span>
          <span class="font-mono text-xs opacity-30 ml-auto">
            ID #{{ snapshotEv?.id }}
          </span>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import { eventsApi, type EventRead } from '@/api/client'
import { useEventsStore } from '@/stores/events'
import { useAuthStore } from '@/stores/auth'


const eventsStore = useEventsStore()
const auth = useAuthStore()
const token = computed(() => auth.token)

// ── Snapshot modal ────────────────────────────────────────────────────────────
const snapshotModal = ref<HTMLDialogElement | null>(null)
const snapshotEv    = ref<EventRead | null>(null)

function openSnapshot(ev: EventRead) {
  snapshotEv.value = ev
  snapshotModal.value?.showModal()
}

// ── Local state — NOT shared store, avoids race with AppLayout.fetchRecent() ──
const rows    = ref<EventRead[]>([])
const loading = ref(false)
const total   = ref(0)

// ── Pagination ────────────────────────────────────────────────────────────────
const PAGE_SIZES  = [10, 25, 50, 100]
const page        = ref(1)
const pageSize    = ref(25)
const hasNextPage = computed(() => page.value * pageSize.value < total.value)

// ── Filters (all server-side) ─────────────────────────────────────────────────
const severity = ref('')
const status   = ref('')
const behavior = ref('')

// New count from local rows (not shared store)
const newCount = computed(() => rows.value.filter(e => e.status === 'NEW').length)

onMounted(() => load())

function resetAndLoad() {
  page.value = 1
  load()
}

function onPageSizeClick(s: number) {
  if (pageSize.value === s) return
  pageSize.value = s
  page.value = 1
  load()
}

function prevPage() { if (page.value > 1) { page.value--; load() } }
function nextPage()  { if (hasNextPage.value) { page.value++; load() } }

async function load() {
  loading.value = true
  try {
    const params: Record<string, string | number> = {
      page:      page.value,
      page_size: pageSize.value,
    }
    if (severity.value) params.severity = severity.value
    if (status.value)   params.status   = status.value
    if (behavior.value) params.behavior  = behavior.value

    const page_data = await eventsApi.list(params)
    rows.value = page_data.items
    total.value = page_data.total
  } catch {
    // keep existing rows on error
  } finally {
    loading.value = false
  }
}

// ── Actions — mutate local rows immediately, also sync store for bell count ───
const busy = ref<Set<number>>(new Set())

async function ack(ev: EventRead) {
  busy.value.add(ev.id)
  try {
    await eventsApi.acknowledge(ev.id)
    ev.status = 'ACKNOWLEDGED'
    eventsStore.acknowledge(ev.id)  // keep store count in sync
  } finally { busy.value.delete(ev.id) }
}

async function silence(ev: EventRead) {
  busy.value.add(ev.id)
  try {
    await eventsApi.silence(ev.id, 300)
    ev.status = 'SILENCED'
    eventsStore.silence(ev.id, 300)
  } finally { busy.value.delete(ev.id) }
}

async function escalate(ev: EventRead) {
  busy.value.add(ev.id)
  try {
    await eventsApi.escalate(ev.id, 'Escalated from console')
    ev.status = 'ESCALATED'
    eventsStore.escalate(ev.id, 'Escalated from console')
  } finally { busy.value.delete(ev.id) }
}

async function ackAll() {
  const targets = rows.value.filter(e => e.status === 'NEW')
  await Promise.allSettled(targets.map(e => ack(e)))
}

// ── Time ──────────────────────────────────────────────────────────────────────
function fmtTime(iso: string) {
  return new Date(iso).toLocaleString([], {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}
function relTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1)  return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return fmtTime(iso)
}

// ── Colors ────────────────────────────────────────────────────────────────────
function rowClass(ev: EventRead) {
  return ev.status === 'SILENCED' ? 'opacity-40' : ''
}
function sevStripClass(s: string) {
  return { critical: 'bg-error', high: 'bg-warning', medium: 'bg-info', low: 'bg-base-300' }[s] ?? 'bg-base-300'
}
function sevClass(s: string) {
  return { critical: 'badge-error', high: 'badge-warning', medium: 'badge-info', low: 'badge-ghost' }[s] ?? 'badge-ghost'
}
function statusClass(s: string) {
  return {
    NEW: 'badge-error', ACKNOWLEDGED: 'badge-success',
    SILENCED: 'badge-ghost', ESCALATED: 'badge-warning',
  }[s] ?? 'badge-ghost'
}
</script>
