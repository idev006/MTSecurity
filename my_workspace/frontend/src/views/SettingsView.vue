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
            <div class="px-4 py-2 border-b border-base-300">
              <h3 class="font-mono text-xs font-semibold opacity-60">CONSOLE THEME</h3>
            </div>
            <div class="p-4">
              <div class="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 gap-2">
                <button v-for="t in themes" :key="t"
                  class="btn btn-sm font-mono relative"
                  :class="currentTheme === t ? 'btn-primary' : 'btn-outline btn-ghost'"
                  @click="setTheme(t)">
                  <span v-if="currentTheme === t"
                    class="absolute -top-1 -right-1 w-2 h-2 bg-success rounded-full"></span>
                  {{ t.toUpperCase() }}
                </button>
              </div>
            </div>

            <!-- Theme preview -->
            <div class="px-4 pb-4">
              <div class="rounded-lg border border-base-300 p-3 flex gap-3 items-center">
                <div class="badge badge-success badge-sm font-mono">ONLINE</div>
                <div class="badge badge-error badge-sm font-mono">ALERT</div>
                <div class="badge badge-warning badge-sm font-mono">WARN</div>
                <div class="badge badge-info badge-sm font-mono">INFO</div>
                <span class="text-xs font-mono opacity-50 ml-auto">PREVIEW</span>
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
            <div class="grid grid-cols-2 sm:grid-cols-3 divide-x divide-y divide-base-300">
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">USERNAME</p>
                <p class="font-mono text-sm mt-0.5">{{ auth.username || '—' }}</p>
              </div>
              <div class="px-4 py-3">
                <p class="font-mono text-xs opacity-50">ROLE</p>
                <p class="font-mono text-sm mt-0.5">{{ auth.role || '—' }}</p>
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

const auth   = useAuthStore()
const system = useSystemStore()
const router = useRouter()

const tab = ref<'system' | 'display' | 'account'>('system')

// ── Theme ─────────────────────────────────────────────────────────────────
const themes = ['light', 'dark', 'corporate', 'dracula', 'night', 'dim', 'cyberpunk', 'forest']
const currentTheme = ref(localStorage.getItem('theme') ?? 'dark')

function setTheme(t: string) {
  currentTheme.value = t
  document.documentElement.setAttribute('data-theme', t)
  localStorage.setItem('theme', t)
}

onMounted(() => {
  document.documentElement.setAttribute('data-theme', currentTheme.value)
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
