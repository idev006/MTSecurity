<template>
  <AppLayout>
    <template #header>
      <h1 class="text-xl font-bold tracking-tight">Zones & Rules</h1>
      <p class="text-sm text-base-content/50 mt-0.5">Manage detection zones and alert rules per camera</p>
    </template>

    <div class="p-4 space-y-4 max-w-5xl mx-auto">

      <!-- Camera selector -->
      <div class="flex items-center gap-3 flex-wrap">
        <span class="text-sm font-medium opacity-60">Camera:</span>
        <button
          v-for="cam in cameras.cameras"
          :key="cam.id"
          class="btn btn-sm"
          :class="selectedCamId === cam.id ? 'btn-primary' : 'btn-ghost'"
          @click="selectCamera(cam.id)"
        >{{ cam.name }}</button>
        <span v-if="cameras.cameras.length === 0" class="text-sm opacity-40">No cameras found</span>
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
                class="border border-base-300 rounded-lg overflow-hidden">
                <!-- Zone header -->
                <div class="flex items-center gap-2 px-3 py-2 bg-base-300/50">
                  <span class="inline-block w-3 h-3 rounded-full flex-shrink-0" :style="`background:${zone.color}`"></span>
                  <span class="font-semibold text-sm flex-1">{{ zone.name }}</span>
                  <span class="badge badge-xs" :class="zone.is_active ? 'badge-success' : 'badge-ghost'">
                    {{ zone.is_active ? 'Active' : 'Inactive' }}
                  </span>
                  <span class="text-xs opacity-40">{{ coordCount(zone) }} pts</span>
                  <button class="btn btn-xs btn-ghost text-error" @click="deleteZone(zone.id)">Delete</button>
                </div>

                <!-- Rules for this zone -->
                <div class="px-3 py-2 space-y-2">
                    <div v-for="rule in rules.filter(r => r.zone_id === zone.id)" :key="rule.id" class="flex items-center gap-2 p-2 bg-base-300/50 rounded-lg hover:bg-base-300 transition-colors">
                      <div :class="['badge badge-xs uppercase font-black px-2', rule.severity === 'critical' ? 'badge-error' : 'badge-info']">{{ rule.severity }}</div>
                      <span class="text-sm font-bold">{{ rule.behavior }}</span>
                      
                      <!-- Advanced Logic Badge -->
                      <div v-if="rule.logic" class="badge badge-primary badge-outline badge-xs gap-1 py-2">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-2 w-2" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                        POLICY
                      </div>

                      <span class="text-[10px] opacity-50 font-mono">cd {{ rule.cooldown_seconds }}s · dw {{ rule.dwell_threshold_seconds }}s</span>
                      
                      <span class="ml-auto flex gap-1">
                        <button type="button" @click="openEditRule(rule)" class="btn btn-xs btn-ghost text-primary px-1 hover:bg-primary/10">
                          <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>
                        </button>
                        <span class="badge badge-xs cursor-pointer" :class="rule.is_active ? 'badge-success' : 'badge-ghost'" @click="toggleRule(rule)">
                          {{ rule.is_active ? 'On' : 'Off' }}
                        </span>
                        <button class="btn btn-xs btn-ghost text-error py-0" @click="deleteRule(rule.id)">×</button>
                      </span>
                    </div>
                  <!-- Add rule form -->
                  <button class="btn btn-xs btn-ghost text-primary gap-1 mt-1"
                    @click="openAddRule(zone.id)">
                    + Add Rule
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

  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import ZoneCanvas from '@/components/ZoneCanvas.vue'
import RuleLogicBuilder from '@/components/RuleLogicBuilder.vue'
import SchedulePicker from '@/components/SchedulePicker.vue'
import { useCamerasStore } from '@/stores/cameras'

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

const cameras = useCamerasStore()
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
    alert('Failed to save zone: ' + e.message)
  }
}

async function deleteZone(id: number) {
  if (!confirm('Delete this zone and all its rules?')) return
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
    alert('Failed to save rule: ' + e.message)
  } finally {
    submitting.value = false
  }
}

async function deleteRule(id: number) {
  await apiDelete(`/rules/${id}`)
  rules.value = rules.value.filter(r => r.id !== id)
}

// ── Init ─────────────────────────────────────────────────────────────────────

onMounted(async () => {
  await cameras.fetchAll()
  if (cameras.cameras.length > 0) {
    await selectCamera(cameras.cameras[0].id)
  }
})
</script>
