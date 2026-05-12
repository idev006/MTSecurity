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

        <!-- ── Cockpit top-right instruments ──────────────────────────── -->
        <div class="flex-none flex items-center gap-1">

          <!-- WS status pill -->
          <div class="badge badge-sm gap-1 font-mono text-xs" :class="wsBadgeClass">
            <span class="inline-block w-1.5 h-1.5 rounded-full" :class="wsDotClass"></span>
            {{ wsLabel }}
          </div>

          <!-- CPU gauge -->
          <div class="hidden sm:flex items-center gap-1 px-2 py-0.5 rounded bg-base-200 text-xs font-mono">
            <span class="opacity-50">CPU</span>
            <span :class="gaugeColor(system.cpuPercent)">{{ system.cpuPercent.toFixed(0) }}%</span>
          </div>

          <!-- RAM gauge -->
          <div class="hidden sm:flex items-center gap-1 px-2 py-0.5 rounded bg-base-200 text-xs font-mono">
            <span class="opacity-50">RAM</span>
            <span :class="gaugeColor(system.ramPercent)">{{ system.ramPercent.toFixed(0) }}%</span>
          </div>

          <!-- Alert bell -->
          <div class="indicator">
            <span v-if="events.newCount > 0"
              class="indicator-item badge badge-error badge-xs animate-pulse">
              {{ events.newCount > 99 ? '99+' : events.newCount }}
            </span>
            <RouterLink to="/events" class="btn btn-ghost btn-circle btn-sm">
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
              </svg>
            </RouterLink>
          </div>

          <!-- User menu -->
          <div class="dropdown dropdown-end">
            <div tabindex="0" role="button" class="btn btn-ghost btn-circle btn-sm avatar placeholder">
              <div class="bg-neutral text-neutral-content rounded-full w-7">
                <span class="text-xs">{{ auth.userInitial }}</span>
              </div>
            </div>
            <ul tabindex="0"
              class="mt-2 z-40 p-2 shadow menu menu-sm dropdown-content bg-base-100 rounded-box w-48 border border-base-300">
              <li class="menu-title text-xs opacity-50">{{ auth.username }} · {{ auth.role }}</li>
              <li><RouterLink to="/settings">Settings</RouterLink></li>
              <li><a class="text-error" @click="handleLogout">Logout</a></li>
            </ul>
          </div>
        </div>
      </div>

      <!-- Page content -->
      <main class="flex-1 p-3 md:p-5 overflow-auto">
        <slot />
      </main>

      <!-- ── Cockpit status bar (always visible at bottom) ──────────────── -->
      <div class="bg-base-100 border-t border-base-300 px-4 py-1 flex items-center gap-4 text-xs font-mono opacity-70">
        <span>UP {{ system.uptime }}</span>
        <span class="opacity-40">|</span>
        <span>CAM {{ system.camerasOnline }}/{{ system.camerasTotal }} ONLINE</span>
        <span class="opacity-40">|</span>
        <span v-if="events.newCount > 0" class="text-error font-semibold">
          {{ events.newCount }} NEW ALERT{{ events.newCount !== 1 ? 'S' : '' }}
        </span>
        <span v-else class="text-success">NO ACTIVE ALERTS</span>
        <span class="ml-auto opacity-40">{{ nowStr }}</span>
      </div>
    </div>

    <!-- ── Sidebar ────────────────────────────────────────────────────────── -->
    <div class="drawer-side z-40">
      <label for="sidebar-drawer" aria-label="close sidebar" class="drawer-overlay"></label>
      <aside class="w-60 min-h-full bg-base-100 border-r border-base-300 flex flex-col">

        <!-- Logo -->
        <div class="p-3 border-b border-base-300">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 bg-primary rounded-lg flex items-center justify-center shrink-0">
              <svg class="h-4 w-4 text-primary-content" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
            </div>
            <div>
              <p class="font-bold text-sm leading-none">MTSecurity</p>
              <p class="text-xs opacity-40 mt-0.5">Pilot's Console v2</p>
            </div>
          </div>
        </div>

        <!-- Nav -->
        <ul class="menu menu-sm flex-1 p-2 gap-0.5">
          <li>
            <RouterLink to="/dashboard" active-class="active" class="gap-2.5">
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>
              </svg>
              Dashboard
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/cameras" active-class="active" class="gap-2.5">
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
              Cameras
              <span class="badge badge-sm ml-auto font-mono">{{ cameras.total }}</span>
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/events" active-class="active" class="gap-2.5">
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
              </svg>
              Events
              <span v-if="events.newCount > 0" class="badge badge-sm badge-error ml-auto font-mono animate-pulse">
                {{ events.newCount }}
              </span>
            </RouterLink>
          </li>
          <li>
            <RouterLink to="/settings" active-class="active" class="gap-2.5">
              <svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
              </svg>
              Settings
            </RouterLink>
          </li>
        </ul>

        <!-- Sidebar system mini-gauges -->
        <div class="p-3 border-t border-base-300 space-y-1.5">
          <div class="flex items-center justify-between text-xs">
            <span class="opacity-50 font-mono">CPU</span>
            <div class="flex items-center gap-2 flex-1 mx-2">
              <progress class="progress progress-xs w-full"
                :class="progressColor(system.cpuPercent)"
                :value="system.cpuPercent" max="100"></progress>
            </div>
            <span class="font-mono" :class="gaugeColor(system.cpuPercent)">
              {{ system.cpuPercent.toFixed(0) }}%
            </span>
          </div>
          <div class="flex items-center justify-between text-xs">
            <span class="opacity-50 font-mono">RAM</span>
            <div class="flex items-center gap-2 flex-1 mx-2">
              <progress class="progress progress-xs w-full"
                :class="progressColor(system.ramPercent)"
                :value="system.ramPercent" max="100"></progress>
            </div>
            <span class="font-mono" :class="gaugeColor(system.ramPercent)">
              {{ system.ramPercent.toFixed(0) }}%
            </span>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCamerasStore } from '@/stores/cameras'
import { useEventsStore } from '@/stores/events'
import { useSystemStore } from '@/stores/system'

const auth    = useAuthStore()
const cameras = useCamerasStore()
const events  = useEventsStore()
const system  = useSystemStore()
const router  = useRouter()
const route   = useRoute()

const pageTitles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/cameras':   'Camera Grid',
  '/events':    'Events & Alerts',
  '/settings':  'Settings',
}
const pageTitle = computed(() => pageTitles[route.path] ?? 'MTSecurity')

// ── WebSocket indicator ────────────────────────────────────────────────────
const wsBadgeClass = computed(() => ({
  'badge-success':   system.isOnline,
  'badge-warning':   system.wsState === 'connecting',
  'badge-error':     system.wsState === 'error' || system.wsState === 'disconnected',
}))
const wsDotClass = computed(() => ({
  'bg-success animate-pulse': system.isOnline,
  'bg-warning':               system.wsState === 'connecting',
  'bg-error':                 !system.isOnline && system.wsState !== 'connecting',
}))
const wsLabel = computed(() => {
  const map: Record<string, string> = {
    connected: 'LIVE', connecting: 'CONN…', error: 'ERR', disconnected: 'OFF'
  }
  return map[system.wsState] ?? 'OFF'
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

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}
</script>
