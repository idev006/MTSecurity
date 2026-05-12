/**
 * System store — health polling + WebSocket lifecycle.
 * Single source of truth for CPU, RAM, uptime, WS connection state.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { healthApi, type HealthResponse } from '@/api/client'
import { useEventsStore } from '@/stores/events'
import { useCamerasStore } from '@/stores/cameras'

type WsState = 'disconnected' | 'connecting' | 'connected' | 'error'

export const useSystemStore = defineStore('system', () => {
  const health = ref<HealthResponse | null>(null)
  const wsState = ref<WsState>('disconnected')
  const lastHealthAt = ref<Date | null>(null)

  let _ws: WebSocket | null = null
  let _pollTimer: ReturnType<typeof setInterval> | null = null
  let _reconnectTimer: ReturnType<typeof setTimeout> | null = null

  const isOnline = computed(() => wsState.value === 'connected')
  const cpuPercent = computed(() => health.value?.system.cpu_percent ?? 0)
  const ramPercent = computed(() => health.value?.system.ram_percent ?? 0)
  const camerasOnline = computed(() => health.value?.cameras.online ?? 0)
  const camerasTotal = computed(() => health.value?.cameras.total ?? 0)
  const uptime = computed(() => {
    const s = health.value?.uptime_seconds ?? 0
    const h = Math.floor(s / 3600)
    const m = Math.floor((s % 3600) / 60)
    return `${h}h ${m}m`
  })

  async function fetchHealth() {
    try {
      health.value = await healthApi.get()
      lastHealthAt.value = new Date()
    } catch { /* server may be down — keep last known state */ }
  }

  function startPolling(intervalMs = 10_000) {
    fetchHealth()
    _pollTimer = setInterval(fetchHealth, intervalMs)
  }

  function stopPolling() {
    if (_pollTimer) clearInterval(_pollTimer)
  }

  function connectWs() {
    if (_ws && (_ws.readyState === WebSocket.OPEN || _ws.readyState === WebSocket.CONNECTING)) return
    const token = localStorage.getItem('access_token')
    if (!token) return

    wsState.value = 'connecting'
    // Relative WS path — proxied by Vite in dev, nginx in prod
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    _ws = new WebSocket(`${proto}://${location.host}/api/v1/ws?token=${token}`)

    _ws.onopen = () => { wsState.value = 'connected' }

    _ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data)
        handleWsMessage(msg)
      } catch { /* malformed */ }
    }

    _ws.onerror = () => { wsState.value = 'error' }

    _ws.onclose = () => {
      wsState.value = 'disconnected'
      _reconnectTimer = setTimeout(connectWs, 5_000)
    }
  }

  function disconnectWs() {
    if (_reconnectTimer) clearTimeout(_reconnectTimer)
    _ws?.close()
    _ws = null
    wsState.value = 'disconnected'
  }

  function handleWsMessage(msg: any) {
    if (msg.type === 'alert_fired') {
      useEventsStore().prependAlert(msg.data)
    }
    if (msg.type === 'frame_ready') {
      useCamerasStore().patchStatus(msg.camera_id, {
        fps: msg.data.fps ?? 0,
        state: 'ONLINE',
        last_frame_at: new Date().toISOString(),
      })
    }
  }

  function subscribeCamera(ids: number[]) {
    _ws?.send(JSON.stringify({ type: 'subscribe', camera_ids: ids }))
  }

  function init() {
    startPolling()
    connectWs()
  }

  function destroy() {
    stopPolling()
    disconnectWs()
  }

  return {
    health, wsState, lastHealthAt,
    isOnline, cpuPercent, ramPercent,
    camerasOnline, camerasTotal, uptime,
    fetchHealth, init, destroy, subscribeCamera,
  }
})
