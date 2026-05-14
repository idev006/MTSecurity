/**
 * Shared UI helper composables.
 * Centralises repeated formatting / colour-mapping logic so each view
 * does NOT need its own copy of gaugeColor, sevClass, etc.
 */

// ── Gauge / progress colours ──────────────────────────────────────────────

/** Tailwind text-colour class based on percentage load. */
export function gaugeColor(pct: number): string {
  if (pct >= 90) return 'text-error'
  if (pct >= 70) return 'text-warning'
  return 'text-success'
}

/** DaisyUI progress colour modifier class based on percentage load. */
export function progressColor(pct: number): string {
  if (pct >= 90) return 'progress-error'
  if (pct >= 70) return 'progress-warning'
  return 'progress-success'
}

// ── Event badge colours ───────────────────────────────────────────────────

const SEV_CLASS: Record<string, string> = {
  critical: 'badge-error',
  high:     'badge-warning',
  medium:   'badge-info',
  low:      'badge-ghost',
}

/** DaisyUI badge class for an alert severity string. */
export function sevBadgeClass(severity: string): string {
  return SEV_CLASS[severity] ?? 'badge-ghost'
}

const STATUS_CLASS: Record<string, string> = {
  NEW:          'badge-error',
  ACKNOWLEDGED: 'badge-success',
  SILENCED:     'badge-ghost',
  ESCALATED:    'badge-warning',
}

/** DaisyUI badge class for an alert status string. */
export function statusBadgeClass(status: string): string {
  return STATUS_CLASS[status] ?? 'badge-ghost'
}

// ── Camera state colours ──────────────────────────────────────────────────

const CAM_DOT_CLASS: Record<string, string> = {
  ONLINE:       'bg-success animate-pulse',
  RECONNECTING: 'bg-warning animate-pulse',
  ERROR:        'bg-error',
  FAILED:       'bg-error',
  CONNECTING:   'bg-info animate-pulse',
  INACTIVE:     'bg-base-300',
}

/** Tailwind bg class for the camera status dot indicator. */
export function camDotClass(state?: string): string {
  return CAM_DOT_CLASS[state ?? 'INACTIVE'] ?? 'bg-base-300'
}

const CAM_BADGE_CLASS: Record<string, string> = {
  ONLINE:       'badge-success',
  RECONNECTING: 'badge-warning',
  ERROR:        'badge-error',
  FAILED:       'badge-error',
  CONNECTING:   'badge-info',
  INACTIVE:     'badge-ghost',
}

/** DaisyUI badge class for the camera state label. */
export function camBadgeClass(state?: string): string {
  return CAM_BADGE_CLASS[state ?? 'INACTIVE'] ?? 'badge-ghost'
}

// ── Time formatting ───────────────────────────────────────────────────────

const TIME_FMT: Intl.DateTimeFormatOptions = {
  hour: '2-digit', minute: '2-digit', second: '2-digit',
}
const DATETIME_FMT: Intl.DateTimeFormatOptions = {
  month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit',
}

/** Format an ISO string to a short time HH:MM:SS. */
export function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], TIME_FMT)
}

/** Format an ISO string to MM/DD HH:MM:SS. */
export function fmtDateTime(iso: string): string {
  return new Date(iso).toLocaleString([], DATETIME_FMT)
}

/** Format a behavior_key to "Behavior Key" style. */
export function fmtBehavior(behavior: string): string {
  return behavior.replace(/_/g, ' ')
}
