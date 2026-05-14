<template>
  <AppLayout>
    <template #header>
      <h1 class="text-xl font-bold tracking-tight">Zones & Rules</h1>
      <p class="text-sm text-base-content/50 mt-0.5">Manage detection zones and alert rules per camera</p>
    </template>

    <div class="p-4 space-y-4 max-w-5xl mx-auto">

      <!-- Camera selector — tabs-boxed style -->
      <div class="flex items-center gap-3 flex-wrap">
        <div class="tabs tabs-boxed bg-base-200 p-0.5">
          <button
            v-for="cam in cameras.cameras"
            :key="cam.id"
            class="tab font-mono text-xs gap-1.5"
            :class="selectedCamId === cam.id ? 'tab-active' : ''"
            @click="selectCamera(cam.id)">
            {{ cam.name }}
            <span class="w-1.5 h-1.5 rounded-full"
              :class="cameras.statusOf(cam.id)?.state === 'ONLINE' ? 'bg-success' :
                      cameras.statusOf(cam.id)?.state === 'ERROR'  ? 'bg-error' :
                      cameras.statusOf(cam.id)?.state === 'RECONNECTING' ? 'bg-warning' :
                      'bg-base-content/20'"></span>
          </button>
        </div>
        <span v-if="cameras.cameras.length === 0" class="text-sm opacity-40 font-mono">NO CAMERAS</span>
      </div>

      <template v-if="selectedCam">
        <!-- Zone list -->
        <div class="card bg-base-200 shadow-sm">
          <div class="card-body p-4">
            <div class="flex items-center justify-between mb-3">
              <h2 class="card-title text-base">
                Zones on <span class="text-primary ml-1">{{ selectedCam.name }}</span>
              </h2>
              <button class="btn btn-sm btn-primary gap-1" @click="openDrawing">
                <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg>
                Draw Zone
              </button>
            </div>

            <div v-if="loading" class="text-center py-6 opacity-50 text-sm">Loading…</div>

            <div v-else-if="zones.length === 0" class="text-center py-6 opacity-40 text-sm">
              No zones yet — click "Draw Zone" to add one
            </div>

            <div v-else class="space-y-3">
              <div v-for="zone in zones" :key="zone.id"
                class="border border-base-300 rounded-lg overflow-hidden"
                :style="`border-left: 3px solid ${zone.color}`">

                <!-- Zone header -->
                <div class="flex items-center gap-2 px-3 py-2.5 bg-base-200/60">
                  <span class="font-semibold text-sm flex-1 truncate">{{ zone.name }}</span>
                  <span class="badge badge-xs font-mono"
                    :class="zone.is_active ? 'badge-success' : 'badge-ghost'">
                    {{ zone.is_active ? 'ACTIVE' : 'INACTIVE' }}
                  </span>
                  <span class="text-xs opacity-30 font-mono">{{ coordCount(zone) }}pts</span>
                  <button class="btn btn-xs btn-ghost btn-square text-error opacity-50 hover:opacity-100"
                    title="Delete zone" @click="deleteZone(zone.id)">
                    <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                    </svg>
                  </button>
                </div>

                <!-- Rules — 2-line card layout -->
                <div class="px-3 py-2 space-y-1.5">
                  <div v-for="rule in rules.filter(r => r.zone_id === zone.id)" :key="rule.id"
                    class="group flex items-start gap-2.5 px-2.5 py-2 rounded-lg hover:bg-base-200 hover:shadow-sm transition-all duration-150">

                    <!-- Severity badge (vertical alignment top) -->
                    <span class="badge badge-xs font-mono mt-0.5 shrink-0"
                      :class="sevBadge(rule.severity)">
                      {{ rule.severity.slice(0,4).toUpperCase() }}
                    </span>

                    <!-- Rule info — 2 lines -->
                    <div class="flex-1 min-w-0">
                      <div class="flex items-center gap-1.5 flex-wrap">
                        <span class="text-sm font-semibold truncate">{{ rule.name || rule.behavior }}</span>
                        <span v-if="rule.logic"
                          class="badge badge-primary badge-outline badge-xs gap-0.5">
                          <svg class="h-2 w-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3"
                              d="M13 10V3L4 14h7v7l9-11h-7z"/>
                          </svg>
                          POLICY
                        </span>
                      </div>
                      <p class="font-mono text-xs opacity-40 mt-0.5 truncate">
                        {{ rule.behavior.replace(/_/g, ' ') }} ·
                        cd {{ rule.cooldown_seconds }}s ·
                        dw {{ rule.dwell_threshold_seconds }}s ·
                        {{ (rule.confidence_threshold * 100).toFixed(0) }}% conf
                      </p>
                    </div>

                    <!-- Action icons — hover reveal -->
                    <div class="flex items-center gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button class="btn btn-xs btn-square btn-ghost text-primary"
                        title="Edit rule" @click="openEditRule(rule)">
                        <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                            d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/>
                        </svg>
                      </button>
                      <button class="btn btn-xs btn-square btn-ghost"
                        :class="rule.is_active ? 'text-success' : 'opacity-30'"
                        title="Toggle rule" @click="toggleRule(rule)">
                        <svg class="h-3.5 w-3.5" viewBox="0 0 24 24" fill="currentColor">
                          <circle cx="12" cy="12" r="8"/>
                        </svg>
                      </button>
                      <button class="btn btn-xs btn-square btn-ghost text-error"
                        title="Delete rule" @click="deleteRule(rule.id)">
                        <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                      </button>
                    </div>
                  </div>

                  <!-- Add rule button -->
                  <button class="btn btn-xs btn-ghost w-full border border-dashed border-base-300
                                 text-primary opacity-60 hover:opacity-100 gap-1 mt-1"
                    @click="openAddRule(zone.id)">
                    <svg class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/>
                    </svg>
                    ADD RULE
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Zone Canvas Modal -->
    <ZoneCanvas
      v-if="drawing && selectedCam"
      :camera-id="selectedCam.id"
      :camera-name="selectedCam.name"
      :stream-url="streamUrl(selectedCam.id)"
      @cancel="drawing = false"
      @save="onZoneSaved"
    />

    <!-- Add Rule Modal -->
    <div v-if="addRuleZoneId !== null" class="modal modal-open">
      <div class="modal-box max-w-lg scrollbar-thin">
        <h3 class="font-bold mb-4 flex items-center justify-between">
          {{ editingRuleId ? 'Edit Security Rule' : 'Add Security Rule' }}
          <div class="flex items-center gap-2">
            <span class="text-[10px] opacity-50 uppercase">Advanced Logic</span>
            <input type="checkbox" v-model="useAdvancedLogic" class="toggle toggle-xs toggle-primary" />
          </div>
        </h3>

        <form @submit.prevent="submitRule" class="space-y-4">
          <!-- Basic Info -->
          <div class="grid grid-cols-2 gap-3">
            <div class="form-control">
              <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">Rule Name</label>
              <input v-model="ruleForm.name" class="input input-bordered input-sm" required placeholder="e.g. Night Intrusion" />
            </div>
            <div class="form-control">
              <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">Severity</label>
              <select v-model="ruleForm.severity" class="select select-bordered select-sm">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
          </div>

          <!-- Schedule Selection -->
          <SchedulePicker v-model="ruleSchedule" />

          <!-- Logic Builder or Basic Behavior -->
          <div v-if="useAdvancedLogic" class="p-3 bg-base-300/30 rounded-lg border border-base-content/10">
            <label class="label label-text py-0 mb-2 text-[10px] opacity-60 uppercase font-bold">Policy Logic Tree</label>
            <RuleLogicBuilder v-model="logicTree" :zones="zones" />
          </div>

          <div v-else class="space-y-3 p-3 bg-base-200/50 rounded-lg">
            <div class="form-control">
              <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">Primary Behavior</label>
              <select v-model="ruleForm.behavior" class="select select-bordered select-sm">
                <option value="intrusion">Intrusion</option>
                <option value="loitering">Loitering</option>
                <option value="line_crossing">Line Crossing</option>
                <option value="crowd_density">Crowd Density</option>
              </select>
            </div>
          </div>

          <!-- Common Settings -->
          <div class="grid grid-cols-2 gap-3">
            <div class="form-control">
              <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">Cooldown (s)</label>
              <input type="number" v-model.number="ruleForm.cooldown_seconds" min="5" class="input input-bordered input-sm" />
            </div>
            <div class="form-control" v-if="!useAdvancedLogic && ruleForm.behavior === 'loitering'">
              <label class="label label-text py-1 text-[10px] opacity-60 uppercase font-bold">Dwell (s)</label>
              <input type="number" v-model.number="ruleForm.dwell_threshold_seconds" min="5" class="input input-bordered input-sm" />
            </div>
          </div>

          <div class="modal-action mt-6 flex flex-col gap-2">
            <button type="submit" class="btn btn-primary w-full h-10" :disabled="submitting">
              {{ submitting ? 'Saving Policy...' : (editingRuleId ? 'Update Security Policy' : 'Save Security Policy') }}
            </button>
            <button type="button" class="btn btn-ghost w-full btn-sm" @click="addRuleZoneId = null; editingRuleId = null">Cancel</button>
          </div>
        </form>
      </div>
      <div class="modal-backdrop" @click="addRuleZoneId = null; editingRuleId = null"></div>
    </div>

    <!-- Add Zone Name Modal -->
    <div v-if="pendingZone" class="modal modal-open">
      <div class="modal-box max-w-sm">
        <h3 class="font-bold mb-3">Name this Zone</h3>
        <input v-model="pendingZoneName" class="input input-bordered w-full" placeholder="e.g. Front Door, Lobby" autofocus @keydown.enter="confirmZone" />
        <div class="modal-action">
          <button class="btn btn-ghost btn-sm" @click="pendingZone = null">Cancel</button>
          <button class="btn btn-primary btn-sm" @click="confirmZone" :disabled="!pendingZoneName.trim()">Create</button>
        </div>
      </div>
      <div class="modal-backdrop" @click="pendingZone = null"></div>
    </div>

    <!-- Delete Zone Confirm Modal -->
    <dialog class="modal" :class="deleteZoneModalOpen && 'modal-open'">
      <div class="modal-box max-w-sm">
        <h3 class="font-bold font-mono text-base">DELETE ZONE?</h3>
        <p class="text-sm opacity-70 mt-2">This zone and all its rules will be permanently removed. This cannot be undone.</p>
        <div class="modal-action">
          <button class="btn btn-sm btn-ghost font-mono" @click="deleteZoneModalOpen = false; deleteTargetZoneId = null">CANCEL</button>
          <button class="btn btn-sm btn-error font-mono" @click="confirmDeleteZone">DELETE</button>
        </div>
      </div>
      <form method="dialog" class="modal-backdrop" @click="deleteZoneModalOpen = false; deleteTargetZoneId = null">
        <button>close</button>
      </form>
    </dialog>

  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import ZoneCanvas from '@/components/ZoneCanvas.vue'
import RuleLogicBuilder from '@/components/RuleLogicBuilder.vue'
import SchedulePicker from '@/components/SchedulePicker.vue'
import { useCamerasStore } from '@/stores/cameras'
import { useToastStore } from '@/stores/toast'

// ── API types & calls ────────────────────────────────────────────────────────

interface ZoneRead {
  id: number; camera_id: number; name: string
  coordinates: string; color: string; is_active: boolean
}
interface RuleRead {
  id: number; zone_id: number; name: string; behavior: string
  is_active: boolean; confidence_threshold: number
  dwell_threshold_seconds: number; cooldown_seconds: number; severity: string
  logic?: any; schedule?: any
}

const BASE = '/api/v1'
const h = () => ({ Authorization: `Bearer ${localStorage.getItem('access_token')}`, 'Content-Type': 'application/json' })

async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(BASE + path, { headers: h() })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}
async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(BASE + path, { method: 'POST', headers: h(), body: JSON.stringify(body) })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}
async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(BASE + path, { method: 'PATCH', headers: h(), body: JSON.stringify(body) })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}
async function apiDelete(path: string): Promise<void> {
  const r = await fetch(BASE + path, { method: 'DELETE', headers: h() })
  if (!r.ok && r.status !== 204) throw new Error(await r.text())
}

// ── Store & state ────────────────────────────────────────────────────────────

const cameras    = useCamerasStore()
const toastStore = useToastStore()
const selectedCamId = ref<number | null>(null)
const zones = ref<ZoneRead[]>([])
const rules = ref<RuleRead[]>([])
const loading = ref(false)
const drawing = ref(false)
const addRuleZoneId = ref<number | null>(null)
const editingRuleId = ref<number | null>(null)
const submitting = ref(false)
const pendingZone = ref<{ coordinates: [number, number][], color: string } | null>(null)
const pendingZoneName = ref('')
const deleteZoneModalOpen = ref(false)
const deleteTargetZoneId = ref<number | null>(null)

const useAdvancedLogic = ref(false)
const logicTree = ref({
  operator: 'AND',
  conditions: []
})
const ruleSchedule = ref({
  start: '00:00',
  end: '23:59',
  days: [0, 1, 2, 3, 4, 5, 6]
})

const selectedCam = computed(() => cameras.cameras.find(c => c.id === selectedCamId.value) ?? null)

const ruleForm = ref({
  name: '',
  behavior: 'intrusion',
  confidence_threshold: 0.6,
  dwell_threshold_seconds: 30,
  cooldown_seconds: 60,
  severity: 'medium',
})

// ── Helpers ──────────────────────────────────────────────────────────────────

function streamUrl(cameraId: number) {
  const token = localStorage.getItem('access_token') ?? ''
  return `/api/v1/cameras/${cameraId}/stream?token=${token}`
}

function coordCount(zone: ZoneRead) {
  try { return (JSON.parse(zone.coordinates) as unknown[]).length }
  catch { return 0 }
}

// ── Actions ──────────────────────────────────────────────────────────────────

async function selectCamera(id: number) {
  selectedCamId.value = id
  await loadZonesAndRules()
}

async function loadZonesAndRules() {
  if (!selectedCamId.value) return
  loading.value = true
  try {
    const [z, r] = await Promise.all([
      apiGet<ZoneRead[]>(`/zones?camera_id=${selectedCamId.value}`),
      apiGet<RuleRead[]>('/rules'),
    ])
    zones.value = z
    rules.value = r.map(rule => ({
      ...rule,
      logic: typeof rule.logic === 'string' ? JSON.parse(rule.logic) : rule.logic,
      schedule: typeof rule.schedule === 'string' ? JSON.parse(rule.schedule) : rule.schedule
    }))
  } finally {
    loading.value = false
  }
}

function openDrawing() {
  drawing.value = true
}

function onZoneSaved(payload: { coordinates: [number, number][], color: string }) {
  drawing.value = false
  pendingZone.value = payload
  pendingZoneName.value = ''
}

async function confirmZone() {
  if (!pendingZone.value || !selectedCamId.value || !pendingZoneName.value.trim()) return
  try {
    const zone = await apiPost<ZoneRead>('/zones', {
      camera_id: selectedCamId.value,
      name: pendingZoneName.value.trim(),
      coordinates: pendingZone.value.coordinates,
      color: pendingZone.value.color,
    })
    zones.value = [...zones.value, zone]
    pendingZone.value = null
  } catch (e: any) {
    toastStore.push({ type: 'error', title: 'Save Failed', message: 'Failed to save zone: ' + e.message })
  }
}

function deleteZone(id: number) {
  deleteTargetZoneId.value = id
  deleteZoneModalOpen.value = true
}

async function confirmDeleteZone() {
  const id = deleteTargetZoneId.value
  if (!id) return
  deleteZoneModalOpen.value = false
  deleteTargetZoneId.value = null
  await apiDelete(`/zones/${id}`)
  zones.value = zones.value.filter(z => z.id !== id)
  rules.value = rules.value.filter(r => r.zone_id !== id)
}

function openAddRule(zoneId: number) {
  addRuleZoneId.value = zoneId
  editingRuleId.value = null
  ruleForm.value = { name: '', behavior: 'intrusion', confidence_threshold: 0.6, dwell_threshold_seconds: 30, cooldown_seconds: 60, severity: 'medium' }
}

function openEditRule(rule: RuleRead) {
  addRuleZoneId.value = rule.zone_id
  editingRuleId.value = rule.id
  ruleForm.value = {
    name: rule.name,
    behavior: rule.behavior as any,
    confidence_threshold: rule.confidence_threshold,
    dwell_threshold_seconds: rule.dwell_threshold_seconds,
    cooldown_seconds: rule.cooldown_seconds,
    severity: rule.severity as any,
  }
  useAdvancedLogic.value = !!rule.logic
  if (rule.logic) logicTree.value = JSON.parse(JSON.stringify(rule.logic))
  if (rule.schedule) ruleSchedule.value = JSON.parse(JSON.stringify(rule.schedule))
}

async function submitRule() {
  if (submitting.value || !addRuleZoneId.value) return
  submitting.value = true
  try {
    const payload = {
      zone_id: addRuleZoneId.value,
      ...ruleForm.value,
      schedule: ruleSchedule.value,
      logic: useAdvancedLogic.value ? logicTree.value : null
    }
    
    if (editingRuleId.value) {
      const rule = await apiPatch<RuleRead>(`/rules/${editingRuleId.value}`, payload)
      rules.value = rules.value.map(r => r.id === rule.id ? rule : r)
    } else {
      const rule = await apiPost<RuleRead>('/rules', payload)
      rules.value = [...rules.value, rule]
    }
    
    addRuleZoneId.value = null
    editingRuleId.value = null
  } catch (e: any) {
    toastStore.push({ type: 'error', title: 'Save Failed', message: 'Failed to save rule: ' + e.message })
  } finally {
    submitting.value = false
  }
}

async function deleteRule(id: number) {
  await apiDelete(`/rules/${id}`)
  rules.value = rules.value.filter(r => r.id !== id)
}

async function toggleRule(rule: RuleRead) {
  const updated = await apiPatch<RuleRead>(`/rules/${rule.id}`, { is_active: !rule.is_active })
  rules.value = rules.value.map(r => r.id === updated.id ? updated : r)
}

function sevBadge(s: string) {
  return { critical: 'badge-error', high: 'badge-warning', medium: 'badge-info', low: 'badge-ghost' }[s] ?? 'badge-ghost'
}

// ── Init ─────────────────────────────────────────────────────────────────────

onMounted(async () => {
  await cameras.fetchAll()
  if (cameras.cameras.length > 0) {
    await selectCamera(cameras.cameras[0].id)
  }
})
</script>
