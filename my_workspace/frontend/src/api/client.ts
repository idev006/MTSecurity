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
  device_name: string
}

export interface CameraStatus {
  camera_id: number
  state: 'INACTIVE' | 'CONNECTING' | 'ONLINE' | 'RECONNECTING' | 'ERROR' | 'FAILED'
  fps: number
  latency_ms: number
  last_frame_at: string | null
  error_msg: string | null
  tracks: any[] | null
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

export interface EventPage {
  items: EventRead[]
  total: number
  page: number
  page_size: number
}

export interface HealthResponse {
  status: string
  version: string
  uptime_seconds: number
  boot_state: string
  cameras: { total: number; online: number }
  system: { cpu_percent: number; ram_percent: number; platform: string }
  notifications: { line: boolean; discord: boolean; slack: boolean; email: boolean }
  timestamp: string
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  login:   (username: string, password: string) =>
    post<TokenResponse>('/auth/login', { username, password }),
  logout:  (refresh_token?: string) =>
    post<void>('/auth/logout', { refresh_token: refresh_token ?? null }),
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
  enable:       (id: number)               => post<CameraRead>(`/cameras/${id}/enable`, {}),
  disable:      (id: number)               => post<CameraRead>(`/cameras/${id}/disable`, {}),
}

// ── Events ────────────────────────────────────────────────────────────────────

export interface EventPurgeRequest {
  before_dt?: string | null
  camera_id?: number | null
  statuses?: string[] | null
  dry_run?: boolean
}
export interface EventPurgeResponse {
  deleted: number
  dry_run: boolean
}

export const eventsApi = {
  list: (params?: Record<string, string | number>) => {
    const qs = params ? '?' + new URLSearchParams(params as Record<string, string>).toString() : ''
    return get<EventPage>(`/events${qs}`)
  },
  get:        (id: number)   => get<EventRead>(`/events/${id}`),
  acknowledge: (id: number, note?: string) =>
    post<void>(`/events/${id}/acknowledge`, { note }),
  silence: (id: number, duration_seconds: number) =>
    post<void>(`/events/${id}/silence`, { duration_seconds }),
  escalate: (id: number, reason: string) =>
    post<void>(`/events/${id}/escalate`, { reason }),
  deleteEvent: (id: number) => del(`/events/${id}`),
  purge: (body: EventPurgeRequest) =>
    post<EventPurgeResponse>('/events/purge', body),
}

// ── Zones ─────────────────────────────────────────────────────────────────────
export interface ZoneRead {
  id: number
  camera_id: number
  name: string
  coordinates: string // JSON
  color: string
  is_active: boolean
}

export const zonesApi = {
  list: () => get<ZoneRead[]>('/zones'),
  get: (id: number) => get<ZoneRead>(`/zones/${id}`),
  create: (body: unknown) => post<ZoneRead>('/zones', body),
  update: (id: number, body: unknown) => patch<ZoneRead>(`/zones/${id}`, body),
  delete: (id: number) => del(`/zones/${id}`),
  enable:  (id: number) => post<ZoneRead>(`/zones/${id}/enable`, {}),
  disable: (id: number) => post<ZoneRead>(`/zones/${id}/disable`, {}),
}

// ── LPR ───────────────────────────────────────────────────────────────────────
export interface LPRRead {
  id: number
  plate: string
  owner_name: string | null
  description: string | null
  is_active: boolean
}

export const lprApi = {
  list: () => get<LPRRead[]>('/lpr'),
  create: (body: unknown) => post<LPRRead>('/lpr', body),
  delete: (id: number) => del(`/lpr/${id}`),
}

// ── Users ─────────────────────────────────────────────────────────────────────

export interface UserCreate {
  username: string
  password: string
  role: string
  display_name?: string | null
  camera_scope?: string | null
}

export interface UserUpdate {
  display_name?: string | null
  is_active?: boolean
  camera_scope?: string | null
}

export const usersApi = {
  list:   ()                            => get<UserRead[]>('/users'),
  get:    (id: number)                  => get<UserRead>(`/users/${id}`),
  create: (body: UserCreate)            => post<UserRead>('/users', body),
  update: (id: number, body: UserUpdate) => patch<UserRead>(`/users/${id}`, body),
  delete: (id: number)                  => del(`/users/${id}`),
  changePassword: (current_password: string, new_password: string) =>
    post<void>('/users/me/change-password', { current_password, new_password }),
}

// ── Rules ─────────────────────────────────────────────────────────────────────
export interface RuleRead {
  id: number
  zone_id: number
  name: string
  behavior: string
  is_active: boolean
  confidence_threshold: number
  dwell_threshold_seconds: number
  cooldown_seconds: number
  severity: string
  schedule: Record<string, any> | null
  logic: Record<string, any> | null
  behavior_params: Record<string, any> | null
  created_at: string
}

export const rulesApi = {
  list: () => get<RuleRead[]>('/rules'),
  get: (id: number) => get<RuleRead>(`/rules/${id}`),
  create: (body: unknown) => post<RuleRead>('/rules', body),
  update: (id: number, body: unknown) => patch<RuleRead>(`/rules/${id}`, body),
  enable:  (id: number) => post<RuleRead>(`/rules/${id}/enable`, {}),
  disable: (id: number) => post<RuleRead>(`/rules/${id}/disable`, {}),
}

// ── Health ────────────────────────────────────────────────────────────────────

export const healthApi = {
  get: () => get<HealthResponse>('/health'),
}

// ── System Settings ───────────────────────────────────────────────────────────

export interface SystemSetting {
  key: string
  value: string
  label: string
  updated_by: string | null
  updated_at: string
}

export const systemApi = {
  getSettings:    () => get<SystemSetting[]>('/system/settings'),
  updateSetting:  (key: string, value: string) =>
    patch<SystemSetting>('/system/settings', { key, value }),
}
