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

        <div class="alert text-xs font-mono">
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          การเปลี่ยนรหัสผ่านและการจัดการผู้ใช้สำหรับ SUPERADMIN ทำได้ผ่าน API
        </div>
      </template>

    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLayout from '@/components/AppLayout.vue'
import { useAuthStore } from '@/stores/auth'
import { useSystemStore } from '@/stores/system'
import { useThemeStore, ALL_THEMES } from '@/stores/theme'

const auth       = useAuthStore()
const system     = useSystemStore()
const themeStore = useThemeStore()
const router     = useRouter()

const tab = ref<'system' | 'display' | 'account'>('system')

onMounted(() => {
  system.fetchHealth()
})

// ── Auth ──────────────────────────────────────────────────────────────────
async function handleLogout() {
  await auth.logout()
  router.push('/login')
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
</script>
