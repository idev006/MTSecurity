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
  let _destroyed = false

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

    _destroyed = false
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
      if (!_destroyed) {
        _reconnectTimer = setTimeout(connectWs, 5_000)
      }
    }
  }

  function disconnectWs() {
    _destroyed = true
    if (_reconnectTimer) clearTimeout(_reconnectTimer)
    _ws?.close()
    _ws = null
    wsState.value = 'disconnected'
  }

  function handleWsMessage(msg: any) {
    if (msg.type === 'alert_fired') {
      const d = msg.data
      // Map AlertFiredPayload → EventRead shape
      useEventsStore().prependAlert({
        id: d.alert_id,
        camera_id: d.camera_id,
        rule_id: null,
        behavior: d.behavior,
        severity: d.severity,
        confidence: d.confidence ?? 0,
        track_id: null,
        snapshot_url: d.snapshot_url ?? null,
        clip_url: d.clip_url ?? null,
        occurred_at: new Date().toISOString(),
        status: 'NEW',
        acknowledged_at: null,
        acknowledged_by: null,
      })
    }
    if (msg.type === 'camera_status') {
      const stateMap: Record<string, string> = {
        connecting: 'CONNECTING', online: 'ONLINE', reconnecting: 'RECONNECTING',
        error: 'ERROR', failed: 'FAILED', inactive: 'INACTIVE',
      }
      useCamerasStore().patchStatus(msg.camera_id, {
        state: (stateMap[msg.data.status] ?? msg.data.status.toUpperCase()) as any,
        error_msg: msg.data.error_msg ?? null,
      })
    }
    if (msg.type === 'frame_ready') {
      useCamerasStore().patchStatus(msg.camera_id, {
        fps: msg.data.fps ?? 0,
        state: 'ONLINE',
        last_frame_at: new Date().toISOString(),
      })
    }
    if (msg.type === 'track_update') {
      useCamerasStore().patchStatus(msg.camera_id, {
        tracks: msg.data.detections || [],
      } as any)
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
