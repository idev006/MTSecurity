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
          <div v-if="canDelete" class="tooltip tooltip-left" data-tip="Purge events…">
            <button class="btn btn-square btn-xs btn-ghost text-error opacity-60 hover:opacity-100"
              @click="openPurgeModal">
              <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
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
                  <div class="flex items-center gap-1.5 flex-wrap">
                    <span class="badge badge-xs font-mono" :class="statusClass(ev.status)">{{ ev.status }}</span>
                    <span v-if="ev.acknowledged_by" class="text-[10px] opacity-30 font-mono">
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
                    <div v-if="ev.clip_url" class="tooltip tooltip-left" data-tip="Play clip">
                      <button class="btn btn-xs btn-square btn-ghost text-info" @click="openClip(ev)">
                        <svg class="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M8 5v14l11-7z"/>
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
                    <div v-if="canDelete" class="tooltip tooltip-left" data-tip="Delete event">
                      <button class="btn btn-xs btn-square btn-ghost text-error opacity-40 hover:opacity-100"
                        :disabled="busy.has(ev.id)"
                        @click="confirmDeleteOne(ev)">
                        <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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

    <!-- ── Delete single event confirm ─────────────────────────────────────── -->
    <dialog ref="deleteModal" class="modal">
      <div class="modal-box max-w-sm">
        <h3 class="font-mono text-sm font-bold text-error mb-1">DELETE EVENT</h3>
        <p class="text-xs opacity-60 mb-4">
          Event <span class="font-mono font-bold">#{{ deleteTarget?.id }}</span>
          and its snapshot/clip files will be permanently removed.
          This cannot be undone.
        </p>
        <div class="modal-action gap-2">
          <form method="dialog"><button class="btn btn-xs btn-ghost font-mono">CANCEL</button></form>
          <button class="btn btn-xs btn-error font-mono"
            :disabled="deleteWorking"
            @click="doDeleteOne">
            <span v-if="deleteWorking" class="loading loading-spinner loading-xs"></span>
            DELETE
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

    <!-- ── Purge events modal ────────────────────────────────────────────────── -->
    <dialog ref="purgeModal" class="modal">
      <div class="modal-box max-w-md">
        <h3 class="font-mono text-sm font-bold text-error mb-3">PURGE EVENTS</h3>

        <div class="flex flex-col gap-3 text-xs">

          <!-- Date range -->
          <label class="flex flex-col gap-1">
            <span class="font-mono opacity-50">AGE FILTER</span>
            <div class="flex items-center gap-2">
              <input type="range" min="0" max="45" v-model.number="purge.days"
                class="range range-xs range-error flex-1" />
              <span class="font-mono font-bold w-14 text-right">
                {{ purge.days === 0 ? 'ALL' : purge.days + 'd' }}
              </span>
            </div>
            <span class="opacity-40 font-mono text-[10px]">
              {{ purge.days === 0
                ? '⚠ ALL DATES — no age restriction'
                : `Older than ${purge.days} days (before ${purgeBeforeDt!.toLocaleDateString()})` }}
            </span>
          </label>

          <!-- Status filter -->
          <div class="flex flex-col gap-1">
            <div class="flex items-center gap-2">
              <span class="font-mono opacity-50">STATUS</span>
              <span class="font-mono text-[10px] opacity-40">
                {{ purge.statuses.length === 0 ? '(all statuses)' : '' }}
              </span>
            </div>
            <div class="flex flex-wrap gap-2">
              <label v-for="s in PURGE_STATUSES" :key="s" class="flex items-center gap-1.5 cursor-pointer">
                <input type="checkbox" class="checkbox checkbox-xs checkbox-error"
                  :value="s" v-model="purge.statuses" />
                <span class="font-mono">{{ s }}</span>
              </label>
            </div>
          </div>

          <!-- Preview result -->
          <div v-if="purge.previewCount !== null"
            :class="purge.previewCount > 0
              ? 'rounded bg-error/10 border border-error/30 px-3 py-2 font-mono'
              : 'rounded bg-base-200 border border-base-300 px-3 py-2 font-mono opacity-60'">
            <span :class="purge.previewCount > 0 ? 'text-error font-bold' : ''">
              {{ purge.previewCount }}
            </span>
            event{{ purge.previewCount !== 1 ? 's' : '' }} match
            <span v-if="purge.previewCount > 0"> — will be permanently deleted</span>
            <span v-else> — nothing to delete</span>
          </div>
          <p v-if="purge.error" class="text-error font-mono text-xs">{{ purge.error }}</p>
        </div>

        <div class="modal-action gap-2 mt-4">
          <form method="dialog">
            <button class="btn btn-xs btn-ghost font-mono" @click="resetPurge">CANCEL</button>
          </form>
          <button class="btn btn-xs btn-outline font-mono"
            :disabled="purge.working"
            @click="previewPurge">
            <span v-if="purge.working && purge.previewCount === null" class="loading loading-spinner loading-xs"></span>
            PREVIEW
          </button>
          <button class="btn btn-xs btn-error font-mono"
            :disabled="purge.working || purge.previewCount === null || purge.previewCount === 0"
            @click="doPurge">
            <span v-if="purge.working && purge.previewCount !== null" class="loading loading-spinner loading-xs"></span>
            DELETE {{ purge.previewCount ?? '' }}
          </button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop"><button @click="resetPurge">close</button></form>
    </dialog>

    <!-- ── Clip player modal ───────────────────────────────────────────────── -->
    <dialog ref="clipModal" class="modal" @close="stopClip">
      <div class="modal-box max-w-3xl p-0 overflow-hidden bg-black">
        <!-- Header -->
        <div class="flex items-center gap-3 px-4 py-2 bg-base-200/80">
          <span class="font-mono text-xs font-bold">
            {{ clipEv?.behavior.replace(/_/g, ' ').toUpperCase() }}
          </span>
          <span class="badge badge-xs font-mono" :class="sevClass(clipEv?.severity ?? '')">
            {{ (clipEv?.severity ?? '').toUpperCase() }}
          </span>
          <span class="font-mono text-xs opacity-50 ml-auto">
            CAM {{ clipEv?.camera_id }} · ID #{{ clipEv?.id }}
          </span>
          <button class="btn btn-xs btn-ghost btn-circle ml-1" @click="clipModal?.close()">✕</button>
        </div>
        <!-- Video -->
        <video
          ref="videoEl"
          class="w-full max-h-[70vh] bg-black"
          controls
          autoplay
          :src="clipEv ? `${clipEv.clip_url}?token=${token}` : undefined"
        ></video>
      </div>
      <form method="dialog" class="modal-backdrop"><button>close</button></form>
    </dialog>

  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive, watch } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import { eventsApi, type EventRead } from '@/api/client'
import { useEventsStore } from '@/stores/events'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'


const eventsStore = useEventsStore()
const auth = useAuthStore()
const toast = useToastStore()
const token = computed(() => auth.token)
const canDelete = computed(() => auth.role === 'SUPERADMIN' || auth.role === 'ADMIN')

// ── Snapshot modal ────────────────────────────────────────────────────────────
const snapshotModal = ref<HTMLDialogElement | null>(null)
const snapshotEv    = ref<EventRead | null>(null)

function openSnapshot(ev: EventRead) {
  snapshotEv.value = ev
  snapshotModal.value?.showModal()
}

// ── Clip player modal ─────────────────────────────────────────────────────────
const clipModal = ref<HTMLDialogElement | null>(null)
const videoEl   = ref<HTMLVideoElement | null>(null)
const clipEv    = ref<EventRead | null>(null)

function openClip(ev: EventRead) {
  clipEv.value = ev
  clipModal.value?.showModal()
}

function stopClip() {
  if (videoEl.value) {
    videoEl.value.pause()
    videoEl.value.src = ''
  }
  clipEv.value = null
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

// ── Delete single ─────────────────────────────────────────────────────────────
const deleteModal  = ref<HTMLDialogElement | null>(null)
const deleteTarget = ref<EventRead | null>(null)
const deleteWorking = ref(false)

function confirmDeleteOne(ev: EventRead) {
  deleteTarget.value = ev
  deleteModal.value?.showModal()
}

async function doDeleteOne() {
  if (!deleteTarget.value) return
  deleteWorking.value = true
  try {
    await eventsApi.deleteEvent(deleteTarget.value.id)
    rows.value = rows.value.filter(r => r.id !== deleteTarget.value!.id)
    total.value = Math.max(0, total.value - 1)
    eventsStore.remove(deleteTarget.value.id)
    deleteModal.value?.close()
  } catch (e: any) {
    toast.error('Delete Failed', e?.message ?? 'Could not delete event')
  } finally {
    deleteWorking.value = false
    deleteTarget.value = null
  }
}

// ── Purge modal ────────────────────────────────────────────────────────────────
const PURGE_STATUSES = ['NEW', 'ACKNOWLEDGED', 'SILENCED', 'ESCALATED']
const purgeModal = ref<HTMLDialogElement | null>(null)

const purge = reactive({
  days: 0,                        // 0 = all time (no date filter)
  statuses: [] as string[],       // empty = all statuses
  previewCount: null as number | null,
  working: false,
  error: '',
})

// null = no date filter (delete all regardless of age)
const purgeBeforeDt = computed<Date | null>(() => {
  if (purge.days === 0) return null
  const d = new Date()
  d.setDate(d.getDate() - purge.days)
  return d
})

function openPurgeModal() {
  resetPurge()
  purgeModal.value?.showModal()
}

function resetPurge() {
  purge.days = 0
  purge.statuses = []
  purge.previewCount = null
  purge.working = false
  purge.error = ''
}

// Reset preview when filter changes so stale count doesn't remain
watch(() => [purge.days, purge.statuses.length], () => { purge.previewCount = null })

function _purgeBody(dry_run: boolean) {
  return {
    before_dt: purgeBeforeDt.value ? purgeBeforeDt.value.toISOString() : null,
    statuses:  purge.statuses.length ? purge.statuses : null,
    dry_run,
  }
}

async function previewPurge() {
  purge.working = true
  purge.error = ''
  purge.previewCount = null
  try {
    const res = await eventsApi.purge(_purgeBody(true))
    purge.previewCount = res.deleted
  } catch (e: any) {
    purge.error = e?.message ?? 'Preview failed'
  } finally {
    purge.working = false
  }
}

async function doPurge() {
  purge.working = true
  purge.error = ''
  try {
    const res = await eventsApi.purge(_purgeBody(false))
    purgeModal.value?.close()
    resetPurge()
    await load()
    eventsStore.fetch()
    toast.success('Purged', `${res.deleted} event(s) deleted successfully`)
  } catch (e: any) {
    purge.error = e?.message ?? 'Purge failed'
  } finally {
    purge.working = false
  }
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
