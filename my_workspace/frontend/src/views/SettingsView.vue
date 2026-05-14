<template>
  <AppLayout>
    <div class="flex flex-col gap-4 max-w-4xl">

      <h2 class="font-mono font-semibold tracking-wide text-sm">SYSTEM SETTINGS</h2>

      <!-- ── Tab bar ──────────────────────────────────────────────────── -->
      <div role="tablist" class="tabs tabs-bordered">
        <button role="tab" class="tab font-mono text-xs"
          :class="tab === 'system' && 'tab-active'" @click="tab = 'system'">SYSTEM</button>
        <button role="tab" class="tab font-mono text-xs"
          :class="tab === 'display' && 'tab-active'" @click="tab = 'display'">DISPLAY</button>
        <button role="tab" class="tab font-mono text-xs"
          :class="tab === 'account' && 'tab-active'" @click="tab = 'account'">ACCOUNT</button>
      </div>

      <!-- ══════════════════════════════════════════════════════════════ -->
      <!-- TAB: SYSTEM                                                    -->
      <!-- ══════════════════════════════════════════════════════════════ -->
      <template v-if="tab === 'system'">

        <!-- System health card -->
        <div class="card bg-base-100 border border-base-300 shadow-none">
          <div class="card-body p-0">
            <div class="px-4 py-2 border-b border-base-300 flex items-center justify-between">
              <h3 class="font-mono text-xs font-semibold opacity-60">SYSTEM STATUS</h3>
              <span class="badge badge-xs font-mono"
                :class="system.health?.status === 'ok' ? 'badge-success' : 'badge-error'">
                {{ system.health?.status?.toUpperCase() ?? 'UNKNOWN' }}
              </span>
            </div>

            <div v-if="!system.health" class="flex justify-center py-8">
              <span class="loading loading-spinner loading-sm opacity-40"></span>
            </div>

            <div v-else class="grid grid-cols-2 sm:grid-cols-3 divide-x divide-y divide-base-300">
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">VERSION</p>
                <p class="font-mono text-sm mt-0.5">{{ system.health.version }}</p>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">UPTIME</p>
                <p class="font-mono text-sm mt-0.5">{{ system.uptime }}</p>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">PLATFORM</p>
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
                <p class="font-mono text-xs opacity-50">BOOT STATE</p>
                <p class="font-mono text-sm mt-0.5">{{ system.health.boot_state }}</p>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">CAMERAS</p>
                <p class="font-mono text-sm mt-0.5">
                  <span class="text-success">{{ system.camerasOnline }}</span>
                  <span class="opacity-40">/{{ system.camerasTotal }}</span> ONLINE
                </p>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">WEBSOCKET</p>
                <p class="font-mono text-sm mt-0.5"
                  :class="system.isOnline ? 'text-success' : 'text-error'">
                  {{ system.wsState.toUpperCase() }}
                </p>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">LAST POLL</p>
                <p class="font-mono text-sm mt-0.5 opacity-60">
                  {{ system.lastHealthAt ? fmtTime(system.lastHealthAt) : '—' }}
                </p>
              </div>
            </div>

            <div class="px-4 py-2 border-t border-base-300">
              <button class="btn btn-xs btn-ghost font-mono" @click="system.fetchHealth()">
                ↻ REFRESH
              </button>
            </div>
          </div>
        </div>

        <!-- Notification channels status -->
        <div class="card bg-base-100 border border-base-300 shadow-none">
          <div class="card-body p-0">
            <div class="px-4 py-2 border-b border-base-300">
              <h3 class="font-mono text-xs font-semibold opacity-60">NOTIFICATION CHANNELS</h3>
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
                    {{ ch.configured ? 'CONFIGURED' : 'NOT SET' }}
                  </span>
                  <p class="text-xs opacity-40 font-mono">via .env</p>
                </div>
              </div>
            </div>
          </div>
        </div>

      </template>

      <!-- ══════════════════════════════════════════════════════════════ -->
      <!-- TAB: DISPLAY                                                   -->
      <!-- ══════════════════════════════════════════════════════════════ -->
      <template v-if="tab === 'display'">
        <div class="card bg-base-100 border border-base-300 shadow-none">
          <div class="card-body p-0">
            <div class="px-4 py-2 border-b border-base-300 flex items-center justify-between">
              <h3 class="font-mono text-xs font-semibold opacity-60">CONSOLE THEME</h3>
              <span class="badge badge-xs badge-ghost font-mono uppercase">{{ themeStore.currentTheme }}</span>
            </div>

            <!-- Theme grid with color swatches -->
            <div class="p-4">
              <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
                <button v-for="t in ALL_THEMES" :key="t"
                  class="btn btn-sm font-mono justify-start gap-2 relative overflow-hidden"
                  :class="themeStore.currentTheme === t ? 'btn-primary' : 'btn-ghost border border-base-300'"
                  @click="themeStore.setTheme(t)">
                  <span v-if="themeStore.currentTheme === t"
                    class="absolute -top-0.5 -right-0.5 w-2 h-2 bg-success rounded-full"></span>
                  <!-- Color swatch dots (isolated with data-theme so they show the target theme colors) -->
                  <span :data-theme="t" class="inline-flex gap-0.5 shrink-0">
                    <span class="w-2.5 h-2.5 rounded-full bg-primary"></span>
                    <span class="w-2.5 h-2.5 rounded-full bg-secondary"></span>
                    <span class="w-2.5 h-2.5 rounded-full bg-accent"></span>
                  </span>
                  <span class="truncate text-xs">{{ t }}</span>
                </button>
              </div>
            </div>

            <!-- Theme semantic color preview -->
            <div class="px-4 pb-4 border-t border-base-300 pt-3">
              <p class="font-mono text-xs opacity-40 mb-2">PREVIEW — CURRENT THEME</p>
              <div class="flex flex-wrap gap-2 items-center">
                <div class="badge badge-success badge-sm font-mono">ONLINE</div>
                <div class="badge badge-error badge-sm font-mono">ALERT</div>
                <div class="badge badge-warning badge-sm font-mono">WARN</div>
                <div class="badge badge-info badge-sm font-mono">INFO</div>
                <div class="badge badge-primary badge-sm font-mono">PRIMARY</div>
                <div class="badge badge-secondary badge-sm font-mono">SECONDARY</div>
                <div class="badge badge-accent badge-sm font-mono">ACCENT</div>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- ══════════════════════════════════════════════════════════════ -->
      <!-- TAB: ACCOUNT                                                   -->
      <!-- ══════════════════════════════════════════════════════════════ -->
      <template v-if="tab === 'account'">
        <div class="card bg-base-100 border border-base-300 shadow-none">
          <div class="card-body p-0">
            <div class="px-4 py-2 border-b border-base-300">
              <h3 class="font-mono text-xs font-semibold opacity-60">CURRENT SESSION</h3>
            </div>

            <!-- Avatar + identity row -->
            <div class="flex items-center gap-4 px-5 py-5 border-b border-base-300">
              <!-- Role-colored avatar circle -->
              <div class="w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold shrink-0"
                :class="avatarClass(auth.role)">
                {{ auth.userInitial || '?' }}
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <p class="font-bold text-sm font-mono">{{ auth.username || '—' }}</p>
                  <span class="badge badge-xs font-mono" :class="roleBadge(auth.role)">{{ auth.role || 'VIEWER' }}</span>
                </div>
                <p class="text-xs opacity-40 font-mono mt-0.5">AUTHENTICATED OPERATOR</p>
              </div>
            </div>

            <!-- Session stats grid -->
            <div class="grid grid-cols-2 sm:grid-cols-3 divide-x divide-y divide-base-300">
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">USERNAME</p>
                <p class="font-mono text-sm mt-0.5">{{ auth.username || '—' }}</p>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">ROLE</p>
                <span class="badge badge-sm font-mono mt-1" :class="roleBadge(auth.role)">{{ auth.role || '—' }}</span>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">STATUS</p>
                <p class="font-mono text-sm mt-0.5 text-success">AUTHENTICATED</p>
              </div>
            </div>

            <div class="px-4 py-3 border-t border-base-300">
              <button class="btn btn-sm btn-error btn-outline font-mono" @click="handleLogout">
                SIGN OUT
              </button>
            </div>
          </div>
        </div>

        <div class="alert text-xs font-mono">
          <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          Password changes and user management are available to SUPERADMIN via the API.
        </div>
      </template>

    </div>
  </AppLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
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

// ── Notification channels (config presence shown, values never exposed) ──
const channels = [
  { name: 'LINE Messaging', icon: '💬', desc: 'LINE_CHANNEL_ACCESS_TOKEN', configured: false },
  { name: 'Discord',        icon: '🎮', desc: 'DISCORD_WEBHOOK_URL',        configured: false },
  { name: 'Slack',          icon: '📢', desc: 'SLACK_WEBHOOK_URL',           configured: false },
  { name: 'Email (SMTP)',   icon: '📧', desc: 'SMTP_HOST + SMTP_USER',       configured: false },
  { name: 'MQTT',           icon: '📡', desc: 'mqtt://broker:1883',          configured: false },
  { name: 'Webhook',        icon: '🔗', desc: 'Generic HTTP POST',           configured: false },
]

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
