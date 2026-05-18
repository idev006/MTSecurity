<template>
  <AppLayout>
    <div class="flex flex-col gap-4 max-w-4xl">

      <h2 class="font-mono font-semibold tracking-wide text-sm">การตั้งค่าระบบ</h2>

      <!-- ── Tab bar ──────────────────────────────────────────────────── -->
      <div role="tablist" class="tabs tabs-bordered">
        <button role="tab" class="tab font-mono text-xs"
          :class="tab === 'system' && 'tab-active'" @click="tab = 'system'">ระบบ</button>
        <button role="tab" class="tab font-mono text-xs"
          :class="tab === 'display' && 'tab-active'" @click="tab = 'display'">การแสดงผล</button>
        <button role="tab" class="tab font-mono text-xs"
          :class="tab === 'account' && 'tab-active'" @click="tab = 'account'">บัญชีผู้ใช้</button>
      </div>

      <!-- ══════════════════════════════════════════════════════════════ -->
      <!-- TAB: ระบบ                                                      -->
      <!-- ══════════════════════════════════════════════════════════════ -->
      <template v-if="tab === 'system'">

        <!-- System health card -->
        <div class="card bg-base-100 border border-base-300 shadow-none">
          <div class="card-body p-0">
            <div class="px-4 py-2 border-b border-base-300 flex items-center justify-between">
              <h3 class="font-mono text-xs font-semibold opacity-60">สถานะระบบ</h3>
              <span class="badge badge-xs font-mono"
                :class="system.health?.status === 'ok' ? 'badge-success' : 'badge-error'">
                {{ system.health?.status === 'ok' ? 'ปกติ' : (system.health?.status?.toUpperCase() ?? 'ไม่ทราบ') }}
              </span>
            </div>

            <div v-if="!system.health" class="flex justify-center py-8">
              <span class="loading loading-spinner loading-sm opacity-40"></span>
            </div>

            <div v-else class="grid grid-cols-2 sm:grid-cols-3 divide-x divide-y divide-base-300">
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">เวอร์ชัน</p>
                <p class="font-mono text-sm mt-0.5">{{ system.health.version }}</p>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">เวลาทำงาน</p>
                <p class="font-mono text-sm mt-0.5">{{ system.uptime }}</p>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">แพลตฟอร์ม</p>
                <p class="font-mono text-sm mt-0.5">{{ system.health.system.platform }}</p>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">CPU</p>
                <div class="flex items-center gap-2 mt-1">
                  <progress class="progress progress-xs flex-1"
                    :class="progressClass(system.cpuPercent)"
                    :value="system.cpuPercent" max="100"></progress>
                  <span class="font-mono text-xs" :class="gaugeColor(system.cpuPercent)">
                    {{ system.cpuPercent.toFixed(0) }}%
                  </span>
                </div>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">RAM</p>
                <div class="flex items-center gap-2 mt-1">
                  <progress class="progress progress-xs flex-1"
                    :class="progressClass(system.ramPercent)"
                    :value="system.ramPercent" max="100"></progress>
                  <span class="font-mono text-xs" :class="gaugeColor(system.ramPercent)">
                    {{ system.ramPercent.toFixed(0) }}%
                  </span>
                </div>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">สถานะบูต</p>
                <p class="font-mono text-sm mt-0.5">{{ system.health.boot_state }}</p>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">กล้อง</p>
                <p class="font-mono text-sm mt-0.5">
                  <span class="text-success">{{ system.camerasOnline }}</span>
                  <span class="opacity-40">/{{ system.camerasTotal }}</span> ออนไลน์
                </p>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">WebSocket</p>
                <p class="font-mono text-sm mt-0.5"
                  :class="system.isOnline ? 'text-success' : 'text-error'">
                  {{ system.wsState.toUpperCase() }}
                </p>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">ตรวจสอบล่าสุด</p>
                <p class="font-mono text-sm mt-0.5 opacity-60">
                  {{ system.lastHealthAt ? fmtTime(system.lastHealthAt) : '—' }}
                </p>
              </div>
            </div>

            <div class="px-4 py-2 border-t border-base-300">
              <button class="btn btn-xs btn-ghost font-mono" @click="system.fetchHealth()">
                ↻ รีเฟรช
              </button>
            </div>
          </div>
        </div>

        <!-- Token settings — ADMIN+ only -->
        <div v-if="auth.role === 'SUPERADMIN' || auth.role === 'ADMIN'"
          class="card bg-base-100 border border-base-300 shadow-none">
          <div class="card-body p-0">
            <div class="px-4 py-2 border-b border-base-300 flex items-center justify-between">
              <h3 class="font-mono text-xs font-semibold opacity-60">การตั้งค่า Token</h3>
              <span class="badge badge-xs badge-ghost font-mono">JWT</span>
            </div>

            <div v-if="tokenLoading" class="flex justify-center py-6">
              <span class="loading loading-spinner loading-sm opacity-40"></span>
            </div>

            <div v-else class="p-4 flex flex-col gap-4">
              <!-- Access token expiry -->
              <div class="flex items-center justify-between gap-4">
                <div class="flex-1 min-w-0">
                  <p class="font-mono text-xs font-semibold">Access Token Expiry</p>
                  <p class="text-xs opacity-50 mt-0.5">อายุของ access token หลัง login</p>
                </div>
                <select v-model="tokenForm.access_minutes"
                  class="select select-bordered select-sm font-mono w-32 shrink-0">
                  <option :value="15">15 นาที</option>
                  <option :value="30">30 นาที</option>
                  <option :value="60">1 ชั่วโมง</option>
                  <option :value="120">2 ชั่วโมง</option>
                  <option :value="240">4 ชั่วโมง</option>
                  <option :value="480">8 ชั่วโมง</option>
                </select>
              </div>

              <!-- Refresh token expiry -->
              <div class="flex items-center justify-between gap-4">
                <div class="flex-1 min-w-0">
                  <p class="font-mono text-xs font-semibold">Refresh Token Expiry</p>
                  <p class="text-xs opacity-50 mt-0.5">อายุของ refresh token (ต้อง login ใหม่หลังหมดอายุ)</p>
                </div>
                <select v-model="tokenForm.refresh_days"
                  class="select select-bordered select-sm font-mono w-32 shrink-0">
                  <option :value="1">1 วัน</option>
                  <option :value="3">3 วัน</option>
                  <option :value="7">7 วัน</option>
                  <option :value="14">14 วัน</option>
                  <option :value="30">30 วัน</option>
                  <option :value="90">90 วัน</option>
                </select>
              </div>

              <p class="text-xs opacity-40 font-mono">
                หมายเหตุ: การเปลี่ยนค่านี้มีผลกับ token ที่ออกใหม่เท่านั้น token ที่มีอยู่แล้วไม่ได้รับผลกระทบ
              </p>

              <div class="flex items-center gap-2">
                <button class="btn btn-primary btn-sm font-mono"
                  :disabled="tokenSaving"
                  @click="saveTokenSettings">
                  <span v-if="tokenSaving" class="loading loading-spinner loading-xs"></span>
                  บันทึก
                </button>
                <span v-if="tokenSaveMsg"
                  class="text-xs font-mono"
                  :class="tokenSaveMsg.startsWith('✓') ? 'text-success' : 'text-error'">
                  {{ tokenSaveMsg }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Evidence quality settings — ADMIN+ only -->
        <div v-if="auth.role === 'SUPERADMIN' || auth.role === 'ADMIN'"
          class="card bg-base-100 border border-base-300 shadow-none">
          <div class="card-body p-0">
            <div class="px-4 py-2 border-b border-base-300 flex items-center justify-between">
              <h3 class="font-mono text-xs font-semibold opacity-60">คุณภาพหลักฐาน (Snapshot & Clip)</h3>
              <span class="badge badge-xs badge-ghost font-mono">EVIDENCE</span>
            </div>

            <div v-if="qualityLoading" class="flex justify-center py-6">
              <span class="loading loading-spinner loading-sm opacity-40"></span>
            </div>

            <div v-else class="p-4 flex flex-col gap-4">
              <!-- Stream Tier -->
              <div class="flex items-center justify-between gap-4">
                <div class="flex-1 min-w-0">
                  <p class="font-mono text-xs font-semibold">ความละเอียด Live Stream</p>
                  <p class="text-xs opacity-50 mt-0.5">Pilot's Console และทุกหน้าที่ดูกล้องแบบ realtime</p>
                </div>
                <select v-model="qualityForm.stream_tier"
                  class="select select-bordered select-sm font-mono w-36 shrink-0">
                  <option value="THUMBNAIL">THUMBNAIL — 320×180</option>
                  <option value="MONITOR">MONITOR — 640×360</option>
                  <option value="DETAIL">DETAIL — 1280×720</option>
                </select>
              </div>

              <!-- Evidence Tier -->
              <div class="flex items-center justify-between gap-4">
                <div class="flex-1 min-w-0">
                  <p class="font-mono text-xs font-semibold">ความละเอียดหลักฐาน</p>
                  <p class="text-xs opacity-50 mt-0.5">ใช้กับทั้ง Snapshot ภาพนิ่ง และ Video Clip</p>
                </div>
                <select v-model="qualityForm.evidence_tier"
                  class="select select-bordered select-sm font-mono w-36 shrink-0">
                  <option value="MONITOR">MONITOR — 640×360</option>
                  <option value="DETAIL">DETAIL — 1280×720</option>
                  <option value="EVIDENCE">EVIDENCE — ต้นฉบับ</option>
                </select>
              </div>

              <!-- Clip CRF -->
              <div class="flex items-center justify-between gap-4">
                <div class="flex-1 min-w-0">
                  <p class="font-mono text-xs font-semibold">Video CRF</p>
                  <p class="text-xs opacity-50 mt-0.5">ยิ่งต่ำยิ่งคมชัด แต่ไฟล์ใหญ่ขึ้น (18–28)</p>
                </div>
                <select v-model="qualityForm.clip_crf"
                  class="select select-bordered select-sm font-mono w-36 shrink-0">
                  <option :value="18">18 — คมชัดสูงสุด</option>
                  <option :value="20">20 — คมชัดมาก</option>
                  <option :value="23">23 — สมดุล (default)</option>
                  <option :value="26">26 — ประหยัดพื้นที่</option>
                  <option :value="28">28 — ประหยัดสูงสุด</option>
                </select>
              </div>

              <div class="alert alert-warning py-2 text-xs font-mono gap-2">
                <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                </svg>
                <span>ความละเอียด (Evidence Tier) มีผลหลัง restart server — Video CRF มีผลทันที</span>
              </div>

              <div class="flex items-center gap-2">
                <button class="btn btn-primary btn-sm font-mono"
                  :disabled="qualitySaving"
                  @click="saveQualitySettings">
                  <span v-if="qualitySaving" class="loading loading-spinner loading-xs"></span>
                  บันทึก
                </button>
                <span v-if="qualitySaveMsg"
                  class="text-xs font-mono"
                  :class="qualitySaveMsg.startsWith('✓') ? 'text-success' : 'text-error'">
                  {{ qualitySaveMsg }}
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Notification channels status -->
        <div class="card bg-base-100 border border-base-300 shadow-none">
          <div class="card-body p-0">
            <div class="px-4 py-2 border-b border-base-300">
              <h3 class="font-mono text-xs font-semibold opacity-60">ช่องทางการแจ้งเตือน</h3>
            </div>
            <div class="divide-y divide-base-300">
              <div v-for="ch in channels" :key="ch.name"
                class="flex items-center justify-between px-4 py-2.5">
                <div class="flex items-center gap-3">
                  <span class="text-lg">{{ ch.icon }}</span>
                  <div>
                    <p class="text-sm font-semibold font-mono">{{ ch.name }}</p>
                    <p class="text-xs opacity-50">{{ ch.desc }}</p>
                  </div>
                </div>
                <div class="flex items-center gap-2">
                  <span class="badge badge-xs font-mono"
                    :class="ch.configured ? 'badge-success' : 'badge-ghost'">
                    {{ ch.configured ? 'ตั้งค่าแล้ว' : 'ยังไม่ตั้งค่า' }}
                  </span>
                  <p class="text-xs opacity-40 font-mono">via .env</p>
                </div>
              </div>
            </div>
          </div>
        </div>

      </template>

      <!-- ══════════════════════════════════════════════════════════════ -->
      <!-- TAB: การแสดงผล                                                 -->
      <!-- ══════════════════════════════════════════════════════════════ -->
      <template v-if="tab === 'display'">
        <div class="card bg-base-100 border border-base-300 shadow-none">
          <div class="card-body p-0">
            <div class="px-4 py-2 border-b border-base-300 flex items-center justify-between">
              <h3 class="font-mono text-xs font-semibold opacity-60">ธีมหน้าจอ</h3>
              <span class="badge badge-xs badge-ghost font-mono uppercase">{{ themeStore.currentTheme }}</span>
            </div>

            <div class="p-4">
              <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                <button v-for="t in ALL_THEMES" :key="t"
                  class="btn btn-sm font-mono justify-start gap-2 relative overflow-hidden"
                  :class="themeStore.currentTheme === t ? 'btn-primary' : 'btn-ghost border border-base-300'"
                  @click="themeStore.setTheme(t)">
                  <span v-if="themeStore.currentTheme === t"
                    class="absolute -top-0.5 -right-0.5 w-2 h-2 bg-success rounded-full"></span>
                  <span :data-theme="t" class="inline-flex gap-0.5 shrink-0">
                    <span class="w-2.5 h-2.5 rounded-full bg-primary"></span>
                    <span class="w-2.5 h-2.5 rounded-full bg-secondary"></span>
                    <span class="w-2.5 h-2.5 rounded-full bg-accent"></span>
                  </span>
                  <span class="truncate text-xs">{{ t }}</span>
                </button>
              </div>
            </div>

            <div class="px-4 pb-4 border-t border-base-300 pt-3">
              <p class="font-mono text-xs opacity-40 mb-2">ตัวอย่าง — ธีมปัจจุบัน</p>
              <div class="flex flex-wrap gap-2 items-center">
                <div class="badge badge-success badge-sm font-mono">ออนไลน์</div>
                <div class="badge badge-error badge-sm font-mono">แจ้งเตือน</div>
                <div class="badge badge-warning badge-sm font-mono">เตือน</div>
                <div class="badge badge-info badge-sm font-mono">ข้อมูล</div>
                <div class="badge badge-primary badge-sm font-mono">หลัก</div>
                <div class="badge badge-secondary badge-sm font-mono">รอง</div>
                <div class="badge badge-accent badge-sm font-mono">เน้น</div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- ══════════════════════════════════════════════════════════════ -->
      <!-- TAB: บัญชีผู้ใช้                                               -->
      <!-- ══════════════════════════════════════════════════════════════ -->
      <template v-if="tab === 'account'">
        <div class="card bg-base-100 border border-base-300 shadow-none">
          <div class="card-body p-0">
            <div class="px-4 py-2 border-b border-base-300">
              <h3 class="font-mono text-xs font-semibold opacity-60">เซสชันปัจจุบัน</h3>
            </div>

            <div class="flex items-center gap-4 px-5 py-5 border-b border-base-300">
              <div class="w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold shrink-0"
                :class="avatarClass(auth.role)">
                {{ auth.userInitial || '?' }}
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <p class="font-bold text-sm font-mono">{{ auth.username || '—' }}</p>
                  <span class="badge badge-xs font-mono" :class="roleBadge(auth.role)">{{ auth.role || 'VIEWER' }}</span>
                </div>
                <p class="text-xs opacity-40 font-mono mt-0.5">ผู้ปฏิบัติงานที่ยืนยันตัวตนแล้ว</p>
              </div>
            </div>

            <div class="grid grid-cols-2 sm:grid-cols-3 divide-x divide-y divide-base-300">
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">ชื่อผู้ใช้</p>
                <p class="font-mono text-sm mt-0.5">{{ auth.username || '—' }}</p>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">สิทธิ์</p>
                <span class="badge badge-sm font-mono mt-1" :class="roleBadge(auth.role)">{{ auth.role || '—' }}</span>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">สถานะ</p>
                <p class="font-mono text-sm mt-0.5 text-success">ยืนยันตัวตนแล้ว</p>
              </div>
            </div>

            <div class="px-4 py-3 border-t border-base-300">
              <button class="btn btn-sm btn-error btn-outline font-mono" @click="handleLogout">
                ออกจากระบบ
              </button>
            </div>
          </div>
        </div>

        <!-- Change password card -->
        <div class="card bg-base-100 border border-base-300 shadow-none">
          <div class="card-body p-0">
            <div class="px-4 py-2 border-b border-base-300">
              <h3 class="font-mono text-xs font-semibold opacity-60">เปลี่ยนรหัสผ่าน</h3>
            </div>
            <div class="px-4 py-4 flex flex-col gap-3 max-w-sm">
              <label class="form-control w-full">
                <div class="label py-0.5">
                  <span class="label-text font-mono text-xs">รหัสผ่านปัจจุบัน</span>
                </div>
                <input v-model="pwForm.current" type="password"
                  class="input input-bordered input-sm font-mono"
                  :class="pwErrors.current ? 'input-error' : ''"
                  placeholder="รหัสผ่านปัจจุบัน" />
                <div v-if="pwErrors.current" class="label py-0.5">
                  <span class="label-text-alt text-error font-mono text-xs">{{ pwErrors.current }}</span>
                </div>
              </label>

              <label class="form-control w-full">
                <div class="label py-0.5">
                  <span class="label-text font-mono text-xs">รหัสผ่านใหม่</span>
                </div>
                <input v-model="pwForm.newPw" type="password"
                  class="input input-bordered input-sm font-mono"
                  :class="pwErrors.newPw ? 'input-error' : ''"
                  placeholder="อย่างน้อย 8 ตัว" />
                <div v-if="pwErrors.newPw" class="label py-0.5">
                  <span class="label-text-alt text-error font-mono text-xs">{{ pwErrors.newPw }}</span>
                </div>
              </label>

              <label class="form-control w-full">
                <div class="label py-0.5">
                  <span class="label-text font-mono text-xs">ยืนยันรหัสผ่านใหม่</span>
                </div>
                <input v-model="pwForm.confirm" type="password"
                  class="input input-bordered input-sm font-mono"
                  :class="pwErrors.confirm ? 'input-error' : ''"
                  placeholder="พิมพ์รหัสผ่านใหม่อีกครั้ง" />
                <div v-if="pwErrors.confirm" class="label py-0.5">
                  <span class="label-text-alt text-error font-mono text-xs">{{ pwErrors.confirm }}</span>
                </div>
              </label>

              <div v-if="pwError" class="alert alert-error py-2 text-xs font-mono">{{ pwError }}</div>
              <div v-if="pwSuccess" class="alert alert-success py-2 text-xs font-mono">{{ pwSuccess }}</div>

              <button class="btn btn-sm btn-primary font-mono self-start"
                :class="pwSaving ? 'loading' : ''"
                :disabled="pwSaving"
                @click="handleChangePassword">
                บันทึกรหัสผ่าน
              </button>
            </div>
          </div>
        </div>

        <!-- Users link for admin roles -->
        <div v-if="auth.role === 'SUPERADMIN' || auth.role === 'ADMIN'"
          class="alert text-xs font-mono">
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
          <span>จัดการผู้ใช้งานทั้งหมดได้ที่</span>
          <RouterLink to="/users" class="link link-primary font-bold">หน้า Users</RouterLink>
        </div>
      </template>

    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'
import { useSystemStore } from '@/stores/system'
import { useThemeStore, ALL_THEMES } from '@/stores/theme'
import { usersApi, systemApi } from '@/api/client'

const auth       = useAuthStore()
const system     = useSystemStore()
const themeStore = useThemeStore()
const router     = useRouter()

const tab = ref<'system' | 'display' | 'account'>('system')

onMounted(() => {
  system.fetchHealth()
  if (auth.role === 'SUPERADMIN' || auth.role === 'ADMIN') {
    loadTokenSettings()
    loadQualitySettings()
  }
})

// ── Token settings (ADMIN+) ───────────────────────────────────────────────
const tokenLoading  = ref(false)
const tokenSaving   = ref(false)
const tokenSaveMsg  = ref('')
const tokenForm     = ref({ access_minutes: 60, refresh_days: 7 })

async function loadTokenSettings() {
  tokenLoading.value = true
  try {
    const settings = await systemApi.getSettings()
    for (const s of settings) {
      if (s.key === 'jwt_access_token_expire_minutes' && s.value)
        tokenForm.value.access_minutes = Number(s.value)
      if (s.key === 'jwt_refresh_token_expire_days' && s.value)
        tokenForm.value.refresh_days = Number(s.value)
    }
  } catch { /* ignore — uses defaults */ }
  finally { tokenLoading.value = false }
}

async function saveTokenSettings() {
  tokenSaving.value = true
  tokenSaveMsg.value = ''
  try {
    await systemApi.updateSetting('jwt_access_token_expire_minutes', String(tokenForm.value.access_minutes))
    await systemApi.updateSetting('jwt_refresh_token_expire_days',   String(tokenForm.value.refresh_days))
    tokenSaveMsg.value = '✓ บันทึกแล้ว'
    setTimeout(() => { tokenSaveMsg.value = '' }, 3000)
  } catch (e: any) {
    tokenSaveMsg.value = e?.message ?? 'บันทึกไม่สำเร็จ'
  } finally {
    tokenSaving.value = false
  }
}

// ── Evidence quality settings (ADMIN+) ───────────────────────────────────────
const qualityLoading  = ref(false)
const qualitySaving   = ref(false)
const qualitySaveMsg  = ref('')
const qualityForm     = ref({ stream_tier: 'MONITOR', evidence_tier: 'DETAIL', clip_crf: 23 })

async function loadQualitySettings() {
  qualityLoading.value = true
  try {
    const settings = await systemApi.getSettings()
    for (const s of settings) {
      if (s.key === 'stream_tier'   && s.value) qualityForm.value.stream_tier   = s.value
      if (s.key === 'evidence_tier' && s.value) qualityForm.value.evidence_tier = s.value
      if (s.key === 'clip_crf'      && s.value) qualityForm.value.clip_crf      = Number(s.value)
    }
  } catch { /* use defaults */ }
  finally { qualityLoading.value = false }
}

async function saveQualitySettings() {
  qualitySaving.value = true
  qualitySaveMsg.value = ''
  try {
    await systemApi.updateSetting('stream_tier',   qualityForm.value.stream_tier)
    await systemApi.updateSetting('evidence_tier', qualityForm.value.evidence_tier)
    await systemApi.updateSetting('clip_crf',      String(qualityForm.value.clip_crf))
    qualitySaveMsg.value = '✓ บันทึกแล้ว'
    setTimeout(() => { qualitySaveMsg.value = '' }, 3000)
  } catch (e: any) {
    qualitySaveMsg.value = e?.message ?? 'บันทึกไม่สำเร็จ'
  } finally {
    qualitySaving.value = false
  }
}

// ── Notification channels — status from /health (boolean only, no secrets) ──
const channels = computed(() => {
  const n = system.health?.notifications
  return [
    { name: 'LINE Messaging', icon: '💬', desc: 'LINE_CHANNEL_ACCESS_TOKEN', configured: n?.line    ?? false },
    { name: 'Discord',        icon: '🎮', desc: 'DISCORD_WEBHOOK_URL',        configured: n?.discord ?? false },
    { name: 'Slack',          icon: '📢', desc: 'SLACK_WEBHOOK_URL',           configured: n?.slack   ?? false },
    { name: 'Email (SMTP)',   icon: '📧', desc: 'SMTP_HOST + SMTP_USER',       configured: n?.email   ?? false },
    { name: 'MQTT',           icon: '📡', desc: 'mqtt://broker:1883',          configured: false },
    { name: 'Webhook',        icon: '🔗', desc: 'Generic HTTP POST',           configured: false },
  ]
})

// ── Account avatar / role ─────────────────────────────────────────────────
function avatarClass(role?: string) {
  const map: Record<string, string> = {
    SUPERADMIN: 'bg-error text-error-content',
    ADMIN:      'bg-warning text-warning-content',
    OPERATOR:   'bg-primary text-primary-content',
    VIEWER:     'bg-neutral text-neutral-content',
  }
  return map[role ?? ''] ?? 'bg-neutral text-neutral-content'
}
function roleBadge(role?: string) {
  const map: Record<string, string> = {
    SUPERADMIN: 'badge-error',
    ADMIN:      'badge-warning',
    OPERATOR:   'badge-primary',
    VIEWER:     'badge-ghost',
  }
  return map[role ?? ''] ?? 'badge-ghost'
}

// ── Gauges ────────────────────────────────────────────────────────────────
function gaugeColor(pct: number) {
  return pct >= 90 ? 'text-error' : pct >= 70 ? 'text-warning' : 'text-success'
}
function progressClass(pct: number) {
  return pct >= 90 ? 'progress-error' : pct >= 70 ? 'progress-warning' : 'progress-success'
}
function fmtTime(d: Date) {
  return d.toLocaleTimeString()
}

// ── Change password ───────────────────────────────────────────────────────
const pwForm    = ref({ current: '', newPw: '', confirm: '' })
const pwErrors  = ref<Record<string, string>>({})
const pwError   = ref('')
const pwSuccess = ref('')
const pwSaving  = ref(false)

async function handleChangePassword() {
  pwErrors.value  = {}
  pwError.value   = ''
  pwSuccess.value = ''

  const errs: Record<string, string> = {}
  if (!pwForm.value.current) errs.current = 'กรุณาใส่รหัสผ่านปัจจุบัน'
  if (pwForm.value.newPw.length < 8) errs.newPw = 'รหัสผ่านใหม่ต้องมีอย่างน้อย 8 ตัวอักษร'
  if (pwForm.value.newPw !== pwForm.value.confirm) errs.confirm = 'รหัสผ่านไม่ตรงกัน'
  if (Object.keys(errs).length) { pwErrors.value = errs; return }

  pwSaving.value = true
  try {
    await usersApi.changePassword(pwForm.value.current, pwForm.value.newPw)
    pwSuccess.value = 'เปลี่ยนรหัสผ่านเรียบร้อยแล้ว'
    pwForm.value = { current: '', newPw: '', confirm: '' }
  } catch (e: any) {
    pwError.value = e?.message ?? 'เปลี่ยนรหัสผ่านไม่สำเร็จ'
  } finally {
    pwSaving.value = false
  }
}
</script>
