import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { camerasApi, type CameraRead, type CameraStatus, type WebcamDevice } from '@/api/client'

export const useCamerasStore = defineStore('cameras', () => {
  const cameras = ref<CameraRead[]>([])
  const statuses = ref<Record<number, CameraStatus>>({})
  const loading = ref(false)
  const error = ref<string | null>(null)

  const total = computed(() => cameras.value.length)
  const online = computed(() =>
    Object.values(statuses.value).filter(s => s.state === 'ONLINE').length
  )
  const reconnecting = computed(() =>
    Object.values(statuses.value).filter(s => s.state === 'RECONNECTING').length
  )
  const failed = computed(() =>
    Object.values(statuses.value).filter(s => s.state === 'ERROR' || s.state === 'FAILED').length
  )

  async function fetchAll() {
    loading.value = true
    error.value = null
    try {
      cameras.value = await camerasApi.list()
      // Fetch statuses in parallel
      const results = await Promise.allSettled(
        cameras.value.map(c => camerasApi.status(c.id))
      )
      results.forEach((r, i) => {
        if (r.status === 'fulfilled') {
          statuses.value[cameras.value[i].id] = r.value
        }
      })
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  // Called by WebSocket hub for live state updates
  function patchStatus(cameraId: number, patch: Partial<CameraStatus>) {
    const existing = statuses.value[cameraId]
    if (existing) {
      statuses.value[cameraId] = { ...existing, ...patch }
    } else {
      // Camera was added after initial fetchAll — create a minimal status entry
      statuses.value[cameraId] = {
        camera_id: cameraId,
        state: 'CONNECTING',
        fps: 0,
        latency_ms: 0,
        last_frame_at: null,
        error_msg: null,
        tracks: null,
        ...patch,
      } as CameraStatus
    }
  }

  function statusOf(id: number): CameraStatus | null {
    return statuses.value[id] ?? null
  }

  async function addCamera(body: {
    name: string
    source_type: 'rtsp' | 'webcam'
    rtsp_url?: string
    device_index?: number
    device_name?: string
    location?: string
    fps?: number
  }): Promise<CameraRead> {
    const cam = await camerasApi.create(body)
    cameras.value = [...cameras.value, cam]
    // Seed a CONNECTING status immediately; WebSocket will update it in real-time
    statuses.value[cam.id] = {
      camera_id: cam.id,
      state: 'CONNECTING',
      fps: 0,
      latency_ms: 0,
      last_frame_at: null,
      error_msg: null,
      tracks: null,
    } as CameraStatus
    return cam
  }

  async function listWebcams(): Promise<WebcamDevice[]> {
    return camerasApi.listWebcams()
  }

  async function setActive(id: number, isActive: boolean): Promise<void> {
    await camerasApi.update(id, { is_active: isActive })
    const cam = cameras.value.find(c => c.id === id)
    if (cam) cam.is_active = isActive
  }

  async function updateCamera(id: number, body: { name?: string; location?: string; fps?: number }): Promise<CameraRead> {
    const updated = await camerasApi.update(id, body)
    const idx = cameras.value.findIndex(c => c.id === id)
    if (idx !== -1) cameras.value[idx] = updated
    return updated
  }

  async function deleteCamera(id: number): Promise<void> {
    await camerasApi.delete(id)
    cameras.value = cameras.value.filter(c => c.id !== id)
  }

  function reset() {
    cameras.value = []
    statuses.value = {}
    error.value = null
  }

  return {
    cameras, statuses, loading, error,
    total, online, reconnecting, failed,
    fetchAll, patchStatus, statusOf, addCamera, listWebcams, setActive, updateCamera, deleteCamera, reset,
  }
})
