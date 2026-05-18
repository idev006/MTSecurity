/**
 * Parse an ISO datetime string from the backend as UTC.
 *
 * The backend may omit a timezone suffix for naive datetimes that are
 * implicitly UTC (SQLite strips tzinfo on read). Without "Z" the browser
 * interprets the string as local time, causing a +07:00 offset error.
 * This helper appends "Z" when no timezone indicator is present.
 */
export function parseUtcIso(iso: string | null | undefined): Date {
  if (!iso) return new Date(NaN)
  // Already has timezone: "...Z", "...+07:00", "...-05:00"
  const hasZone = /[Z+\-]\d*$/.test(iso.trimEnd())
  return new Date(hasZone ? iso : iso + 'Z')
}

/** Relative time label: "just now", "5m ago", "2h ago", "3d ago" */
export function relTime(iso: string | null | undefined): string {
  const d = parseUtcIso(iso)
  if (isNaN(d.getTime())) return '—'
  const diff = Date.now() - d.getTime()
  const m = Math.floor(diff / 60_000)
  if (m < 1)  return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

/** Short locale datetime string (date + time, no year) */
export function fmtDateTime(iso: string | null | undefined): string {
  const d = parseUtcIso(iso)
  if (isNaN(d.getTime())) return '—'
  return d.toLocaleString([], {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

/** Short locale time string (HH:MM:SS) */
export function fmtTime(iso: string | null | undefined): string {
  const d = parseUtcIso(iso)
  if (isNaN(d.getTime())) return '—'
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
