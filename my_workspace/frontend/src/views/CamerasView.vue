<template>
  <AppLayout>
    <div class="flex flex-col gap-4">

      <!-- ── Toolbar ──────────────────────────────────────────────────── -->
      <div class="flex items-center gap-3 flex-wrap">
        <h2 class="font-mono font-semibold tracking-wide text-sm">CAMERA GRID</h2>
        <div class="ml-auto flex items-center gap-2 flex-wrap">
          <!-- Layout toggle -->
          <div class="join">
            <button class="btn btn-xs join-item font-mono"
              :class="layout === 'grid' ? 'btn-active' : 'btn-ghost'"
              @click="layout = 'grid'">GRID</button>
            <button class="btn btn-xs join-item font-mono"
              :class="layout === 'list' ? 'btn-active' : 'btn-ghost'"
              @click="layout = 'list'">LIST</button>
          </div>
          <!-- Filter -->
          <select class="select select-xs select-bordered font-mono" v-model="filterState">
            <option value="">ALL STATES</option>
            <option value="ONLINE">ONLINE</option>
            <option value="RECONNECTING">RECONNECTING</option>
            <option value="ERROR">ERROR</option>
            <option value="INACTIVE">INACTIVE</option>
          </select>
          <button class="btn btn-xs btn-ghost font-mono" @click="cameras.fetchAll()">
            ↻ REFRESH
          </button>
          <!-- Add webcam -->
          <button class="btn btn-xs btn-primary font-mono" @click="openAddWebcam">
            + WEBCAM
          </button>
        </div>
      </div>

      <!-- ── Summary strip ────────────────────────────────────────────── -->
      <div class="flex gap-3 font-mono text-xs">
        <span class="text-success">● {{ cameras.online }} ONLINE</span>
        <span v-if="cameras.reconnecting" class="text-warning">● {{ cameras.reconnecting }} RECONN</span>
        <span v-if="cameras.failed" class="text-error">● {{ cameras.failed }} ERROR</span>
        <span class="opacity-40">| TOTAL {{ cameras.total }}</span>
        <span class="opacity-40">
          | {{ webcamCount }} WEBCAM{{ webcamCount !== 1 ? 'S' : '' }}
        </span>
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
        class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
        <div v-for="cam in filtered" :key="cam.id"
          class="rounded-lg border bg-base-100 overflow-hidden cursor-pointer transition-all hover:shadow-md"
          :class="cardBorder(cameras.statusOf(cam.id)?.state)"
          @click="selectCam(cam.id)">

          <!-- Video placeholder -->
          <div class="aspect-video bg-base-300 flex items-center justify-center relative">
            <div class="text-center opacity-30">
              <svg class="h-7 w-7 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
                  d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
            </div>
            <!-- State badge overlay -->
            <div class="absolute top-1.5 left-1.5 flex gap-1">
              <span class="badge badge-xs font-mono" :class="stateBadge(cameras.statusOf(cam.id)?.state)">
                {{ cameras.statusOf(cam.id)?.state ?? 'INACTIVE' }}
              </span>
              <span v-if="cam.source_type === 'webcam'" class="badge badge-xs badge-info font-mono">USB</span>
            </div>
            <!-- FPS overlay -->
            <div v-if="cameras.statusOf(cam.id)?.fps"
              class="absolute bottom-1.5 right-1.5 text-xs font-mono opacity-60 bg-base-100/70 px-1 rounded">
              {{ cameras.statusOf(cam.id)?.fps?.toFixed(0) }}fps
            </div>
          </div>

          <!-- Info strip -->
          <div class="px-2 py-1.5 flex items-center justify-between gap-1">
            <div class="min-w-0 flex-1">
              <p class="text-xs font-semibold truncate">{{ cam.name }}</p>
              <p v-if="cam.location" class="text-xs opacity-40 truncate">{{ cam.location }}</p>
              <p v-else-if="cam.source_type === 'webcam'" class="text-xs opacity-30 font-mono">
                DEV {{ cam.device_index }}
              </p>
            </div>
            <div class="flex items-center gap-1 shrink-0" @click.stop>
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
        <table class="table table-sm">
          <thead>
            <tr class="font-mono text-xs opacity-50 border-b border-base-300">
              <th>ID</th><th>NAME</th><th>SOURCE</th><th>LOCATION</th>
              <th>STATE</th><th>FPS</th><th>LATENCY</th><th>LAST FRAME</th>
              <th>ON/OFF</th><th></th>
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
              <td>
                <div v-if="cameras.statusOf(cam.id)?.error_msg"
                  class="tooltip" :data-tip="cameras.statusOf(cam.id)?.error_msg">
                  <svg class="h-4 w-4 text-error" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                  </svg>
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
              @click="form.device_index = dev.index">
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

  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import { useCamerasStore } from '@/stores/cameras'
import type { WebcamDevice } from '@/api/client'

const cameras = useCamerasStore()
const layout = ref<'grid' | 'list'>('grid')
const filterState = ref('')

const filtered = computed(() =>
  cameras.cameras.filter(c =>
    !filterState.value || (cameras.statusOf(c.id)?.state ?? 'INACTIVE') === filterState.value
  )
)

const webcamCount = computed(() =>
  cameras.cameras.filter(c => c.source_type === 'webcam').length
)

function selectCam(_id: number) { /* Phase 5: open live stream modal */ }

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
  fps: 15,
})

async function openAddWebcam() {
  formError.value = ''
  form.value = { name: '', location: '', device_index: null, fps: 15 }
  availableWebcams.value = []
  webcamModal.value?.showModal()
  probing.value = true
  try {
    availableWebcams.value = await cameras.listWebcams()
    if (availableWebcams.value.length === 1) {
      form.value.device_index = availableWebcams.value[0].index
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

function fmtTime(iso: string) {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

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
    ERROR: 'border-error/50', FAILED: 'border-error/50',
    CONNECTING: 'border-info/30', INACTIVE: 'border-base-300',
  }[state ?? 'INACTIVE'] ?? 'border-base-300'
}
</script>
