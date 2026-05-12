/**
 * Typed API client — all requests go to relative /api/v1/* paths,
 * proxied by Vite in dev and served directly in production.
 * Never hardcodes a hostname.
 */

const BASE = '/api/v1'

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const token = localStorage.getItem('access_token')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    window.location.href = '/login'
    throw new ApiError(401, 'Unauthorized')
  }

  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }))
    throw new ApiError(res.status, detail?.detail ?? res.statusText)
  }

  if (res.status === 204) return undefined as T
  return res.json()
}

const get  = <T>(path: string)              => request<T>('GET',    path)
const post = <T>(path: string, body: unknown) => request<T>('POST',   path, body)
const patch = <T>(path: string, body: unknown) => request<T>('PATCH',  path, body)
const del  = (path: string)                  => request<void>('DELETE', path)

// ── Types ─────────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface UserRead {
  id: number
  username: string
  role: string
  is_active: boolean
  display_name: string | null
  camera_scope: string | null
  created_at: string
}

export interface CameraRead {
  id: number
  name: string
  source_type: 'rtsp' | 'webcam'
  device_index: number | null
  location: string | null
  is_active: boolean
  resolution_width: number
  resolution_height: number
  fps: number
  created_at: string
  updated_at: string
}

export interface WebcamDevice {
  index: number
  label: string
}

export interface CameraStatus {
  camera_id: number
  state: 'INACTIVE' | 'CONNECTING' | 'ONLINE' | 'RECONNECTING' | 'ERROR' | 'FAILED'
  fps: number
  latency_ms: number
  last_frame_at: string | null
  error_msg: string | null
}

export interface EventRead {
  id: number
  camera_id: number | null
  rule_id: number | null
  behavior: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  confidence: number
  track_id: number | null
  snapshot_url: string | null
  clip_url: string | null
  occurred_at: string
  status: string
  acknowledged_at: string | null
  acknowledged_by: string | null
}

export interface HealthResponse {
  status: string
  version: string
  uptime_seconds: number
  boot_state: string
  cameras: { total: number; online: number }
  system: { cpu_percent: number; ram_percent: number; platform: string }
  timestamp: string
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  login:   (username: string, password: string) =>
    post<TokenResponse>('/auth/login', { username, password }),
  logout:  () => post<void>('/auth/logout', {}),
  refresh: (refresh_token: string) =>
    post<TokenResponse>('/auth/refresh', { refresh_token }),
  me:      () => get<UserRead>('/auth/me'),
}

// ── Cameras ───────────────────────────────────────────────────────────────────

export const camerasApi = {
  list:         ()                           => get<CameraRead[]>('/cameras'),
  get:          (id: number)                => get<CameraRead>(`/cameras/${id}`),
  create:       (body: unknown)             => post<CameraRead>('/cameras', body),
  update:       (id: number, body: unknown) => patch<CameraRead>(`/cameras/${id}`, body),
  delete:       (id: number)               => del(`/cameras/${id}`),
  status:       (id: number)               => get<CameraStatus>(`/cameras/${id}/status`),
  listWebcams:  ()                          => get<WebcamDevice[]>('/cameras/webcams'),
}

// ── Events ────────────────────────────────────────────────────────────────────

export const eventsApi = {
  list: (params?: Record<string, string | number>) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : ''
    return get<EventRead[]>(`/events${qs}`)
  },
  get:        (id: number)   => get<EventRead>(`/events/${id}`),
  acknowledge: (id: number, note?: string) =>
    post<void>(`/events/${id}/acknowledge`, { note }),
  silence: (id: number, duration_seconds: number) =>
    post<void>(`/events/${id}/silence`, { duration_seconds }),
  escalate: (id: number, reason: string) =>
    post<void>(`/events/${id}/escalate`, { reason }),
}

// ── Health ────────────────────────────────────────────────────────────────────

export const healthApi = {
  get: () => get<HealthResponse>('/health'),
}
