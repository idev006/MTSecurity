<template>
  <div class="drawer lg:drawer-open">
    <input id="sidebar-drawer" type="checkbox" class="drawer-toggle" />

    <!-- ── Main content area ─────────────────────────────────────────────── -->
    <div class="drawer-content flex flex-col min-h-screen bg-base-200">

      <!-- Top navbar -->
      <div class="navbar bg-base-100 border-b border-base-300 sticky top-0 z-30 shadow-sm px-3 min-h-12 h-12">
        <!-- Hamburger (mobile) -->
        <div class="flex-none lg:hidden">
          <label for="sidebar-drawer" class="btn btn-square btn-ghost btn-sm">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
            </svg>
          </label>
        </div>

        <!-- Page title -->
        <div class="flex-1 px-2">
          <span class="text-sm font-semibold tracking-wide">{{ pageTitle }}</span>
        </div>

        <!-- ── Top-right instruments ──────────────────────────────────── -->
        <div class="flex-none flex items-center gap-1">

          <!-- WS status badge -->
          <div class="badge badge-sm gap-1 font-mono text-xs"
            :class="[wsBadgeClass, system.isOnline ? 'glow-success' : '']">
            <span class="inline-block w-1.5 h-1.5 rounded-full status-breathe" :class="wsDotClass"></span>
            {{ wsLabel }}
          </div>

          <!-- CPU / RAM -->
          <div class="hidden sm:flex items-center gap-1 px-2 py-0.5 rounded bg-base-200 text-xs font-mono">
            <span class="opacity-50">CPU</span>
            <span :class="gaugeColor(system.cpuPercent)">{{ system.cpuPercent.toFixed(0) }}%</span>
          </div>
          <div class="hidden sm:flex items-center gap-1 px-2 py-0.5 rounded bg-base-200 text-xs font-mono">
            <span class="opacity-50">RAM</span>
            <span :class="gaugeColor(system.ramPercent)">{{ system.ramPercent.toFixed(0) }}%</span>
          </div>

          <!-- Theme switcher — DaisyUI dropdown -->
          <div class="dropdown dropdown-end">
            <button tabindex="0" class="btn btn-ghost btn-xs font-mono gap-1 hidden sm:flex" title="Switch theme">
              <svg class="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/>
              </svg>
              <span class="uppercase text-xs">{{ theme.currentTheme }}</span>
            </button>
            <ul tabindex="0"
              class="dropdown-content menu bg-base-100 border border-base-300 rounded-box w-44 z-50 max-h-72 overflow-y-auto shadow-lg p-1 mt-1">
              <li class="menu-title font-mono">THEME</li>
              <li v-for="t in ALL_THEMES" :key="t">
                <a class="font-mono text-xs flex items-center gap-2"
                  :class="t === theme.currentTheme ? 'active' : ''"
                  @click="theme.setTheme(t)">
                  <!-- 3-dot swatch isolated with data-theme -->
                  <span :data-theme="t" class="inline-flex gap-0.5 shrink-0">
                    <span class="w-2 h-2 rounded-full bg-primary"></span>
                    <span class="w-2 h-2 rounded-full bg-secondary"></span>
                    <span class="w-2 h-2 rounded-full bg-accent"></span>
                  </span>
                  {{ t }}
                </a>
              </li>
            </ul>
          </div>

          <!-- Alert bell — DaisyUI indicator -->
          <div class="indicator">
            <span v-if="events.newCount > 0"
              class="indicator-item badge badge-error badge-xs">
              {{ events.newCount > 99 ? '99+' : events.newCount }}
            </span>
            <RouterLink to="/events"
              class="btn btn-ghost btn-circle btn-sm"
              :class="events.newCount > 0 ? 'glow-error' : ''">
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
              </svg>
            </RouterLink>
          </div>

          <!-- User menu — DaisyUI dropdown -->
          <div class="dropdown dropdown-end">
            <div tabindex="0" role="button" class="btn btn-ghost btn-circle btn-sm avatar placeholder">
              <div class="bg-neutral text-neutral-content rounded-full w-7">
                <span class="text-xs">{{ auth.userInitial }}</span>
              </div>
            </div>
            <ul tabindex="0"
              class="mt-2 z-40 p-2 shadow menu menu-sm dropdown-content bg-base-100 rounded-box w-48 border border-base-300">
              <li class="menu-title">{{ auth.username }} · {{ auth.role }}</li>
              <li><RouterLink to="/settings">Settings</RouterLink></li>
              <li><a class="text-error" @click="handleLogout">Logout</a></li>
            </ul>
          </div>

          <!-- ── Logout confirm modal ─────────────────────────────────── -->
          <dialog ref="logoutModal" class="modal">
            <div class="modal-box max-w-sm">
              <h3 class="font-bold font-mono text-base">ออกจากระบบ?</h3>
              <p class="py-3 text-sm opacity-70">
                คุณกำลังจะออกจากระบบในฐานะ
                <span class="font-mono font-bold">{{ auth.username }}</span>
                session ปัจจุบันจะสิ้นสุดทันที
              </p>
              <div class="modal-action gap-2">
                <button class="btn btn-error btn-sm font-mono" @click="confirmLogout">
                  ออกจากระบบ
                </button>
                <form method="dialog">
                  <button class="btn btn-sm font-mono">ยกเลิก</button>
                </form>
              </div>
            </div>
            <form method="dialog" class="modal-backdrop">
              <button>close</button>
            </form>
          </dialog>
        </div>
      </div>

      <!-- Page content -->
      <main class="flex-1 p-3 md:p-5 overflow-auto">
        <slot />
      </main>

      <!-- ── Status bar ─────────────────────────────────────────────────── -->
      <div class="bg-base-100 border-t border-base-300 px-4 py-1 flex items-center gap-4 text-xs font-mono">
        <span class="opacity-50">UP {{ system.uptime }}</span>
        <span class="opacity-20">|</span>
        <span class="opacity-50">CAM {{ system.camerasOnline }}/{{ system.camerasTotal }}</span>
        <span class="opacity-20">|</span>
        <span v-if="events.newCount > 0" class="text-error font-bold animate-pulse">
          ⚠ {{ events.newCount }} ALERT{{ events.newCount !== 1 ? 'S' : '' }}
        </span>
        <span v-else class="text-success opacity-60">● CLEAR</span>
        <span class="ml-auto opacity-30">{{ nowStr }}</span>
      </div>
    </div>

    <!-- ── Sidebar ────────────────────────────────────────────────────────── -->
    <div class="drawer-side z-40">
      <label for="sidebar-drawer" aria-label="close sidebar" class="drawer-overlay"></label>
      <aside class="w-60 min-h-full bg-base-100 border-r border-base-300 flex flex-col">

        <!-- Logo block -->
        <div class="relative overflow-hidden border-b border-base-300">
          <div class="absolute inset-0 bg-gradient-to-br from-primary/15 via-primary/5 to-transparent pointer-events-none"></div>
          <div class="absolute -top-4 -right-4 w-20 h-20 bg-primary/20 rounded-full blur-2xl pointer-events-none"></div>
          <div class="relative flex items-center gap-3 p-4">
            <div class="w-9 h-9 bg-primary rounded-xl flex items-center justify-center shrink-0 shadow-lg shadow-primary/30">
              <svg class="h-5 w-5 text-primary-content" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
            </div>
            <div class="min-w-0">
              <p class="font-bold text-sm leading-none tracking-wide">MTSecurity</p>
              <p class="text-[10px] opacity-40 mt-0.5 font-mono tracking-widest">PILOT CONSOLE</p>
            </div>
            <span class="ml-auto badge badge-xs badge-ghost font-mono opacity-50 shrink-0">v2</span>
          </div>
        </div>

        <!-- Navigation — DaisyUI menu native with active-class -->
        <ul class="menu menu-sm flex-1 p-2 gap-0.5">
          <li class="menu-title font-mono text-[9px] tracking-[0.3em]">NAVIGATION</li>

          <li>
            <RouterLink to="/pilot" active-class="active" class="gap-2.5">
              <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
              Pilot's Console
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/dashboard" active-class="active" class="gap-2.5">
              <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>
              </svg>
              Dashboard
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/cameras" active-class="active" class="gap-2.5">
              <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
              Cameras
              <span class="badge badge-xs badge-ghost ml-auto font-mono">{{ cameras.total }}</span>
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/zones" active-class="active" class="gap-2.5">
              <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>
              </svg>
              Zones & Rules
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/events" active-class="active" class="gap-2.5">
              <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
              </svg>
              Events
              <span v-if="events.newCount > 0"
                class="badge badge-xs badge-error ml-auto font-mono animate-pulse">
                {{ events.newCount }}
              </span>
            </RouterLink>
          </li>
          <li v-if="auth.role === 'SUPERADMIN' || auth.role === 'ADMIN'">
            <RouterLink to="/users" active-class="active" class="gap-2.5">
              <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
              </svg>
              Users
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/settings" active-class="active" class="gap-2.5">
              <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              Settings
            </RouterLink>
          </li>
        </ul>

        <!-- System Health footer -->
        <div class="p-3 border-t border-base-300 space-y-2.5">
          <div class="flex items-center justify-between">
            <p class="text-[9px] tracking-[0.3em] opacity-30 font-mono uppercase">System Health</p>
            <div class="flex items-center gap-1">
              <span class="w-1.5 h-1.5 rounded-full status-breathe"
                :class="system.isOnline ? 'bg-success' : 'bg-error'"></span>
              <span class="font-mono text-[9px] opacity-40">{{ wsLabel }}</span>
            </div>
          </div>
          <div class="space-y-0.5">
            <div class="flex justify-between text-[10px] font-mono">
              <span class="opacity-50">CPU</span>
              <span :class="gaugeColor(system.cpuPercent)">{{ system.cpuPercent.toFixed(0) }}%</span>
            </div>
            <progress class="progress progress-xs w-full" :class="progressColor(system.cpuPercent)"
              :value="system.cpuPercent" max="100"></progress>
          </div>
          <div class="space-y-0.5">
            <div class="flex justify-between text-[10px] font-mono">
              <span class="opacity-50">RAM</span>
              <span :class="gaugeColor(system.ramPercent)">{{ system.ramPercent.toFixed(0) }}%</span>
            </div>
            <progress class="progress progress-xs w-full" :class="progressColor(system.ramPercent)"
              :value="system.ramPercent" max="100"></progress>
          </div>
        </div>
      </aside>
    </div>

    <!-- ── Toast Notifications ─────────────────────────────────────────────── -->
    <div class="toast toast-bottom toast-end z-[100] pointer-events-none">
      <TransitionGroup enter-active-class="transition duration-300 ease-out"
                       enter-from-class="transform translate-y-8 opacity-0"
                       enter-to-class="transform translate-y-0 opacity-100"
                       leave-active-class="transition duration-200 ease-in"
                       leave-from-class="transform translate-y-0 opacity-100"
                       leave-to-class="transform translate-y-8 opacity-0">

        <!-- WebSocket alert toasts -->
        <div v-for="t in activeWsToasts" :key="'ws-' + t.__toastId"
          class="alert shadow-lg pointer-events-auto cursor-pointer"
          :class="t.severity === 'critical' ? 'alert-error' : t.severity === 'high' ? 'alert-warning' : 'alert-info'"
          @click="gotoEvents">
          <svg class="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
          <div>
            <div class="font-bold text-sm font-mono">{{ (t.behavior || 'ALERT').replace(/_/g, ' ').toUpperCase() }}</div>
            <div class="text-xs opacity-80">CAM {{ t.camera_id }} · {{ (t.severity || '').toUpperCase() }}</div>
          </div>
        </div>

        <!-- Programmatic toasts (useToastStore) -->
        <div v-for="t in toastStore.toasts" :key="'ui-' + t.id"
          class="alert shadow-lg pointer-events-auto"
          :class="{
            'alert-success': t.type === 'success',
            'alert-error':   t.type === 'error',
            'alert-warning': t.type === 'warning',
            'alert-info':    t.type === 'info',
          }">
          <svg v-if="t.type === 'success'" class="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <svg v-else-if="t.type === 'error'" class="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <svg v-else class="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <div class="flex-1 min-w-0 font-mono">
            <p v-if="t.title" class="font-bold text-sm">{{ t.title }}</p>
            <p class="text-xs" :class="t.title ? 'opacity-80' : 'font-semibold'">{{ t.message }}</p>
          </div>
          <button class="btn btn-ghost btn-xs shrink-0" @click="toastStore.remove(t.id)">✕</button>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch, nextTick } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCamerasStore } from '@/stores/cameras'
import { useEventsStore } from '@/stores/events'
import { useSystemStore } from '@/stores/system'
import { useToastStore } from '@/stores/toast'
import { useThemeStore, ALL_THEMES } from '@/stores/theme'

const auth       = useAuthStore()
const cameras    = useCamerasStore()
const events     = useEventsStore()
const system     = useSystemStore()
const router     = useRouter()
const route      = useRoute()
const toastStore = useToastStore()
const theme      = useThemeStore()

// ── Page title ────────────────────────────────────────────────────────────
const pageTitles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/cameras':   'Camera Grid',
  '/events':    'Events & Alerts',
  '/settings':  'Settings',
  '/pilot':     "Pilot's Console",
  '/zones':     'Zones & Rules',
  '/users':     'User Management',
}
const pageTitle = computed(() => pageTitles[route.path] ?? 'MTSecurity')

// ── WebSocket status ──────────────────────────────────────────────────────
const wsBadgeClass = computed(() => ({
  'badge-success': system.isOnline,
  'badge-warning': system.wsState === 'connecting',
  'badge-error':   system.wsState === 'error' || system.wsState === 'disconnected',
}))
const wsDotClass = computed(() => ({
  'bg-success': system.isOnline,
  'bg-warning': system.wsState === 'connecting',
  'bg-error':   !system.isOnline && system.wsState !== 'connecting',
}))
const wsLabel = computed(() => {
  return { connected: 'LIVE', connecting: 'CONN…', error: 'ERR', disconnected: 'OFF' }[system.wsState] ?? 'OFF'
})

// ── Gauges ────────────────────────────────────────────────────────────────
function gaugeColor(pct: number) {
  if (pct >= 90) return 'text-error'
  if (pct >= 70) return 'text-warning'
  return 'text-success'
}
function progressColor(pct: number) {
  if (pct >= 90) return 'progress-error'
  if (pct >= 70) return 'progress-warning'
  return 'progress-success'
}

// ── Clock ─────────────────────────────────────────────────────────────────
const nowStr = ref('')
let _clockTimer: ReturnType<typeof setInterval>
function tick() { nowStr.value = new Date().toLocaleTimeString() }
tick()

// ── Lifecycle ─────────────────────────────────────────────────────────────
onMounted(() => {
  system.init()
  cameras.fetchAll()
  events.fetchRecent()
  _clockTimer = setInterval(tick, 1000)
})
onUnmounted(() => {
  system.destroy()
  clearInterval(_clockTimer)
})

const logoutModal = ref<HTMLDialogElement | null>(null)

function handleLogout() {
  logoutModal.value?.showModal()
}

async function confirmLogout() {
  logoutModal.value?.close()
  await auth.logout()
  router.push('/login')
}

// ── WebSocket alert toasts ─────────────────────────────────────────────────
const activeWsToasts = ref<any[]>([])
watch(() => events.latestAlert, (alert) => {
  if (!alert) return
  const t = { ...alert, __toastId: Date.now() + Math.random() }
  activeWsToasts.value.push(t)
  setTimeout(() => {
    activeWsToasts.value = activeWsToasts.value.filter(x => x.__toastId !== t.__toastId)
  }, 6000)
})
function gotoEvents() { router.push('/events') }
</script>
