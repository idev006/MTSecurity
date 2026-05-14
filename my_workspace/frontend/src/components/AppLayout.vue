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

        <!-- Page title with icon -->
        <div class="flex-1 px-2 flex items-center gap-2">
          <component :is="'svg'" class="h-3.5 w-3.5 text-primary opacity-70 hidden sm:block"
            fill="none" viewBox="0 0 24 24" stroke="currentColor" v-html="pageIconPath">
          </component>
          <span class="text-sm font-semibold tracking-wide">{{ pageTitle }}</span>
        </div>

        <!-- ── Cockpit top-right instruments ──────────────────────────── -->
        <div class="flex-none flex items-center gap-1">

          <!-- WS status pill -->
          <div class="badge badge-sm gap-1 font-mono text-xs transition-shadow duration-300"
            :class="[wsBadgeClass, system.isOnline ? 'glow-success' : '']">
            <span class="inline-block w-1.5 h-1.5 rounded-full status-breathe" :class="wsDotClass"></span>
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

          <!-- Theme switcher -->
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
              <li class="menu-title text-xs opacity-50 font-mono px-2 py-1">THEME</li>
              <li v-for="t in ALL_THEMES" :key="t">
                <button class="font-mono text-xs py-1 px-2 rounded w-full text-left flex items-center gap-2"
                  :class="t === theme.currentTheme ? 'bg-primary text-primary-content' : 'hover:bg-base-200'"
                  @click="theme.setTheme(t)">
                  <span :data-theme="t" class="inline-flex gap-0.5 shrink-0">
                    <span class="w-2 h-2 rounded-full bg-primary"></span>
                    <span class="w-2 h-2 rounded-full bg-secondary"></span>
                    <span class="w-2 h-2 rounded-full bg-accent"></span>
                  </span>
                  {{ t }}
                </button>
              </li>
            </ul>
          </div>

          <!-- Alert bell -->
          <div class="indicator">
            <span v-if="events.newCount > 0"
              class="indicator-item badge badge-error badge-xs animate-pulse glow-error">
              {{ events.newCount > 99 ? '99+' : events.newCount }}
            </span>
            <RouterLink to="/events"
              class="btn btn-ghost btn-circle btn-sm transition-shadow duration-300"
              :class="events.newCount > 0 ? 'glow-error' : ''">
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

      <!-- ── Cockpit status bar ──────────────────────────────────────────── -->
      <div class="bg-base-100 border-t border-base-300 px-4 py-1 flex items-center gap-4 text-xs font-mono">
        <span class="opacity-50">UP {{ system.uptime }}</span>
        <span class="opacity-20">|</span>
        <span class="opacity-50">CAM {{ system.camerasOnline }}/{{ system.camerasTotal }} ONLINE</span>
        <span class="opacity-20">|</span>
        <span v-if="events.newCount > 0" class="text-error font-bold tracking-wider animate-pulse">
          ⚠ {{ events.newCount }} NEW ALERT{{ events.newCount !== 1 ? 'S' : '' }}
        </span>
        <span v-else class="text-success opacity-70">● ALL CLEAR</span>
        <span class="ml-auto opacity-30">{{ nowStr }}</span>
      </div>
    </div>

    <!-- ── Sidebar ────────────────────────────────────────────────────────── -->
    <div class="drawer-side z-40">
      <label for="sidebar-drawer" aria-label="close sidebar" class="drawer-overlay"></label>
      <aside class="w-60 min-h-full bg-base-100 border-r border-base-300 flex flex-col">

        <!-- ── Logo block ────────────────────────────────────────────────── -->
        <div class="relative overflow-hidden border-b border-base-300">
          <!-- Gradient background -->
          <div class="absolute inset-0 bg-gradient-to-br from-primary/15 via-primary/5 to-transparent pointer-events-none"></div>
          <!-- Decorative blur orb -->
          <div class="absolute -top-4 -right-4 w-20 h-20 bg-primary/20 rounded-full blur-2xl pointer-events-none"></div>

          <div class="relative flex items-center gap-3 p-4">
            <!-- Camera icon with glow -->
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
            <!-- Version chip -->
            <span class="ml-auto badge badge-xs badge-ghost font-mono opacity-50 shrink-0">v2</span>
          </div>
        </div>

        <!-- ── Navigation ────────────────────────────────────────────────── -->
        <div class="flex-1 p-2 pt-3 flex flex-col gap-0.5">
          <!-- Section label -->
          <p class="text-[9px] tracking-[0.3em] opacity-30 font-mono px-2 pb-1.5 uppercase">Navigation</p>

          <!-- Nav items — manual active class for nav-active-bg effect -->
          <a v-for="item in navItems" :key="item.path"
            :href="item.path"
            @click.prevent="router.push(item.path)"
            class="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors duration-150"
            :class="isActive(item.path)
              ? 'nav-active-bg text-base-content'
              : 'hover:bg-base-200/70 opacity-70 hover:opacity-100'">
            <svg class="h-4 w-4 shrink-0 transition-colors"
              :class="isActive(item.path) ? 'text-primary' : ''"
              fill="none" viewBox="0 0 24 24" stroke="currentColor"
              v-html="item.iconPath">
            </svg>
            <span :class="isActive(item.path) ? 'font-semibold' : ''">{{ item.label }}</span>
            <!-- Badge for cameras count -->
            <span v-if="item.path === '/cameras'"
              class="badge badge-xs badge-ghost ml-auto font-mono opacity-60">{{ cameras.total }}</span>
            <!-- Badge for new events -->
            <span v-if="item.path === '/events' && events.newCount > 0"
              class="badge badge-xs badge-error ml-auto font-mono animate-pulse">{{ events.newCount }}</span>
          </a>
        </div>

        <!-- ── System Health footer ───────────────────────────────────────── -->
        <div class="p-3 border-t border-base-300 space-y-2.5">
          <!-- Section label -->
          <div class="flex items-center justify-between">
            <p class="text-[9px] tracking-[0.3em] opacity-30 font-mono uppercase">System Health</p>
            <!-- WS indicator -->
            <div class="flex items-center gap-1">
              <span class="w-1.5 h-1.5 rounded-full status-breathe"
                :class="system.isOnline ? 'bg-success' : 'bg-error'"></span>
              <span class="font-mono text-[9px] opacity-40">{{ wsLabel }}</span>
            </div>
          </div>

          <!-- CPU gauge -->
          <div class="space-y-0.5">
            <div class="flex items-center justify-between text-xs">
              <span class="opacity-50 font-mono text-[10px]">CPU</span>
              <span class="font-mono text-[10px]" :class="gaugeColor(system.cpuPercent)">
                {{ system.cpuPercent.toFixed(0) }}%
              </span>
            </div>
            <progress class="progress progress-xs w-full"
              :class="progressColor(system.cpuPercent)"
              :value="system.cpuPercent" max="100"></progress>
          </div>

          <!-- RAM gauge -->
          <div class="space-y-0.5">
            <div class="flex items-center justify-between text-xs">
              <span class="opacity-50 font-mono text-[10px]">RAM</span>
              <span class="font-mono text-[10px]" :class="gaugeColor(system.ramPercent)">
                {{ system.ramPercent.toFixed(0) }}%
              </span>
            </div>
            <progress class="progress progress-xs w-full"
              :class="progressColor(system.ramPercent)"
              :value="system.ramPercent" max="100"></progress>
          </div>
        </div>
      </aside>
    </div>

    <!-- ── Toast Notifications ─────────────────────────────────────────────── -->
    <div class="toast toast-bottom toast-end z-[100] font-mono pointer-events-none space-y-2">
      <TransitionGroup enter-active-class="transition duration-300 ease-out"
                       enter-from-class="transform translate-y-8 opacity-0"
                       enter-to-class="transform translate-y-0 opacity-100"
                       leave-active-class="transition duration-200 ease-in"
                       leave-from-class="transform translate-y-0 opacity-100"
                       leave-to-class="transform translate-y-8 opacity-0">

        <!-- WebSocket alert toasts -->
        <div v-for="t in activeWsToasts" :key="'ws-' + t.__toastId"
          class="alert shadow-lg pointer-events-auto cursor-pointer max-w-sm"
          :class="t.severity === 'critical' ? 'alert-error' : (t.severity === 'high' ? 'alert-warning' : 'alert-info')"
          @click="gotoEvents">
          <svg class="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
          <div>
            <h3 class="font-bold text-sm">{{ (t.behavior || 'ALERT').replace(/_/g, ' ').toUpperCase() }} (CAM {{ t.camera_id }})</h3>
            <div class="text-xs opacity-80">{{ (t.severity || 'UNKNOWN').toUpperCase() }} ALERT</div>
          </div>
        </div>

        <!-- Programmatic toasts (from toastStore) -->
        <div v-for="t in toastStore.toasts" :key="'ui-' + t.id"
          class="alert shadow-lg pointer-events-auto max-w-sm"
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
          <svg v-else-if="t.type === 'warning'" class="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
          </svg>
          <svg v-else class="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <div class="flex-1 min-w-0">
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
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCamerasStore } from '@/stores/cameras'
import { useEventsStore } from '@/stores/events'
import { useSystemStore } from '@/stores/system'
import { useToastStore } from '@/stores/toast'
import { useThemeStore, ALL_THEMES } from '@/stores/theme'

const auth      = useAuthStore()
const cameras   = useCamerasStore()
const events    = useEventsStore()
const system    = useSystemStore()
const router    = useRouter()
const route     = useRoute()
const toastStore = useToastStore()
const theme     = useThemeStore()

// ── Nav items ─────────────────────────────────────────────────────────────
const navItems = [
  {
    path: '/pilot',
    label: "Pilot's Console",
    iconPath: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>',
  },
  {
    path: '/dashboard',
    label: 'Dashboard',
    iconPath: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>',
  },
  {
    path: '/cameras',
    label: 'Cameras',
    iconPath: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>',
  },
  {
    path: '/zones',
    label: 'Zones & Rules',
    iconPath: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>',
  },
  {
    path: '/events',
    label: 'Events',
    iconPath: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>',
  },
  {
    path: '/settings',
    label: 'Settings',
    iconPath: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>',
  },
]

function isActive(path: string) {
  return route.path === path || route.path.startsWith(path + '/')
}

// ── Page title + icon ─────────────────────────────────────────────────────
const pageMeta: Record<string, { title: string; icon: string }> = {
  '/dashboard': {
    title: 'Dashboard',
    icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>',
  },
  '/cameras': {
    title: 'Camera Grid',
    icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>',
  },
  '/events': {
    title: 'Events & Alerts',
    icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>',
  },
  '/settings': {
    title: 'Settings',
    icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>',
  },
  '/pilot': {
    title: "Pilot's Console",
    icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>',
  },
  '/zones': {
    title: 'Zones & Rules',
    icon: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"/>',
  },
}
const pageTitle    = computed(() => pageMeta[route.path]?.title ?? 'MTSecurity')
const pageIconPath = computed(() => pageMeta[route.path]?.icon ?? '')

// ── WebSocket indicator ────────────────────────────────────────────────────
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

// ── WebSocket alert toasts ─────────────────────────────────────────────────
const activeWsToasts = ref<any[]>([])
watch(() => events.latestAlert, (newAlert) => {
  if (newAlert) {
    const t = { ...newAlert, __toastId: Date.now() + Math.random() }
    activeWsToasts.value.push(t)
    setTimeout(() => {
      activeWsToasts.value = activeWsToasts.value.filter(x => x.__toastId !== t.__toastId)
    }, 6000)
  }
})
function gotoEvents() {
  router.push('/events')
}
</script>
