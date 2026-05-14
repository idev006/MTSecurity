# 18 — UI/UX World-Class Overhaul (Mission Control Aesthetic)

## Overview

Complete premium redesign of all MTSecurity v2 frontend views using a "Mission Control / Security Operations Center" aesthetic. Every change is additive and non-destructive to store logic, API calls, WebSocket handlers, and keyboard shortcuts.

**Stack:** Vue 3 + Composition API, Tailwind CSS v4.3, DaisyUI v5.5.19, Pinia

---

## Design Principles

| Principle | Implementation |
|-----------|----------------|
| Information at a glance | Severity strips, glow utilities, color-coded badges |
| Semantic color is law | `error`=danger, `success`=safe, `warning`=caution |
| Monospace telemetry | All numbers/codes in Chakra Petch mono font |
| Glow only where critical | Glow effects on status-critical elements only |
| Premium dark-first | Glass cards, depth layers, gradient highlights |

---

## New Files Created

### `src/stores/theme.ts`
- Exports `ALL_THEMES` array with all 35 DaisyUI themes
- Module-level IIFE applies saved theme at import time (no flash)
- `useThemeStore()` with `currentTheme` and `setTheme(theme)`
- Persists to `localStorage` under key `mt-theme`

```typescript
// Runs before Vue mounts — eliminates theme flash
const _saved = localStorage.getItem('mt-theme') ?? 'dark'
document.documentElement.setAttribute('data-theme', _saved)
```

### `src/stores/toast.ts`
- Global Pinia store for programmatic toasts
- `push({ type, message, title? }, durationMs?)` — auto-removes after timeout
- `remove(id)` — manual dismiss
- `type` values: `'success' | 'error' | 'warning' | 'info'`

```typescript
const toast = useToastStore()
toast.push({ type: 'error', title: 'DELETE FAILED', message: 'Zone not found' })
```

---

## Global CSS Utilities (`src/style.css`)

```css
/* Glow status utilities — oklch-based, theme-aware */
.glow-success    { box-shadow: 0 0 14px oklch(var(--su)/0.40), 0 0 4px oklch(var(--su)/0.25); }
.glow-error      { box-shadow: 0 0 16px oklch(var(--er)/0.50), 0 0 6px oklch(var(--er)/0.30); }
.glow-warning    { box-shadow: 0 0 12px oklch(var(--wa)/0.35), 0 0 4px oklch(var(--wa)/0.20); }
.glow-primary    { box-shadow: 0 0 20px oklch(var(--p)/0.35),  0 0 8px oklch(var(--p)/0.20); }
.glow-primary-sm { box-shadow: 0 0 12px oklch(var(--p)/0.30); }

/* Glassmorphism card */
.glass-card {
  background: oklch(var(--b1)/0.82);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid oklch(var(--bc)/0.09);
}

/* Gradient sidebar active nav */
.nav-active-bg {
  background: linear-gradient(90deg, oklch(var(--p)/0.18) 0%, oklch(var(--p)/0.05) 60%, transparent 100%);
  border-left: 2px solid oklch(var(--p));
  padding-left: calc(0.75rem - 2px);
}

/* Pulsing status dot */
@keyframes status-breathe {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.55; transform: scale(1.25); }
}
.status-breathe { animation: status-breathe 2.4s ease-in-out infinite; }

/* Severity row tints for tables */
.row-critical { background-color: oklch(var(--er)/0.05); border-left: 3px solid oklch(var(--er)); }
.row-high     { background-color: oklch(var(--wa)/0.05); border-left: 3px solid oklch(var(--wa)); }
.row-medium   { border-left: 3px solid oklch(var(--in)/0.6); }
.row-low      { border-left: 3px solid oklch(var(--bc)/0.12); }

/* Stat card hover lift */
.stat-card-hover { transition: transform 0.18s ease, box-shadow 0.18s ease; }
.stat-card-hover:hover { transform: translateY(-2px); box-shadow: 0 6px 24px oklch(var(--bc)/0.10); }
```

---

## View-by-View Changes

### AppLayout.vue
**Highest-impact file — appears on every page**

- **Logo block**: gradient bg (`from-primary/15`), decorative blur orb (`blur-2xl`), camera icon with `shadow-lg shadow-primary/30`, version chip
- **Navigation section label**: `NAVIGATION` in `text-[9px] tracking-[0.3em] opacity-30 font-mono`
- **Active nav items**: route-aware `isActive(path)` function applies `nav-active-bg` gradient class + `text-primary` icon color; no DaisyUI `active-class` conflict
- **Inactive nav items**: `opacity-70 hover:opacity-100` with `hover:bg-base-200/70`
- **WS status badge**: adds `glow-success` CSS class when `system.isOnline`
- **Alert bell button**: adds `glow-error` when `events.newCount > 0`
- **SYSTEM HEALTH footer**: section label + WS dot indicator + CPU/RAM mini-gauges with labels
- **Dual-track toasts**: WebSocket alert toasts + Pinia-store programmatic toasts, both animated with `TransitionGroup`

### LoginView.vue
- Card changed from `bg-base-100` to `glass-card glow-primary-sm` (glassmorphism + subtle glow)
- Logo ring gets `glow-primary` (strong primary halo)
- Show/hide password toggle with eye/eye-off SVGs

### DashboardView.vue
- All 4 stat cards get `stat-card-hover` (translateY lift on hover)
- Active Alerts card adds `glow-error` when `events.newCount > 0`
- Relative time (`relTime()`) on alert table timestamps

### EventsView.vue
- Bulk action bar: `backdrop-blur-sm glow-error` for dramatic alert presence
- Table: `table-pin-rows` for sticky header on scroll
- Severity left-strip: 1px wide `<div>` in first `<td>` with `sevStripClass()`
- Hover-reveal action buttons: snapshot, ACK, silence, escalate

### PilotView.vue
**Major surgical redesign — no logic changes**

**Alert Queue:**
- Header: `status-breathe` animated dot (green when clear, red when alerts), badge with count
- Alert items: left color strip (`w-1`) by severity + 2-line layout (badge + behavior name + camera on line 1; confidence% + relative time on line 2)
- Hover-reveal: VIEW and ACK buttons slide in
- Empty state: success-glow circle with checkmark icon

**Telemetry card:**
- DaisyUI `stats stats-horizontal` 3-column layout: CPU | RAM | CAMERAS
- Each stat: `stat-title` + `stat-value` + progress bar or badge
- Uptime row below stats
- Shortcut legend: `kbd kbd-xs` components with descriptive labels

### SettingsView.vue
**Account tab:**
- Avatar circle (`w-14 h-14`) with user initial, colored by role:
  - `SUPERADMIN` → `bg-error text-error-content`
  - `ADMIN` → `bg-warning text-warning-content`
  - `OPERATOR` → `bg-primary text-primary-content`
  - `VIEWER` → `bg-neutral text-neutral-content`
- Role badge next to username (colored via `roleBadge()` helper)
- Session stats grid preserved

### ZonesView.vue
- Rule items: `hover:shadow-sm transition-all duration-150` for lift on hover
- Camera selector: `tabs tabs-boxed` with status dot per camera tab
- Delete confirm: DaisyUI `<dialog>` modal (no browser `confirm()`)
- Rule layout: 2-line card — severity badge + name + policy badge on line 1; meta info on line 2

### CamerasView.vue
- `cardBorder()` helper: ERROR/FAILED states now include `glow-error` in addition to border class
- Toolbar: section icon, improved toggle buttons, summary strip badges

---

## Constraint Compliance

| Constraint | Status |
|-----------|--------|
| No store/API logic changes | ✅ All stores untouched |
| No new npm dependencies | ✅ DaisyUI + Tailwind only |
| PilotView keyboard shortcuts preserved | ✅ `handleKeydown()` unchanged |
| v-model bindings preserved | ✅ All reactive refs preserved |
| WebSocket handlers preserved | ✅ No changes to ws/event logic |

---

## Theme Architecture

```
localStorage['mt-theme']
        ↓
stores/theme.ts (module IIFE) → document.documentElement.setAttribute('data-theme', ...)
        ↓
useThemeStore().currentTheme  ← reactive ref for UI
        ↓
AppLayout theme switcher dropdown (35 themes × 3-dot color swatches)
SettingsView display tab (35-theme grid)
```

The `:data-theme="t"` attribute on swatch dots isolates each button to show that theme's own `bg-primary`, `bg-secondary`, `bg-accent` colors — without affecting the surrounding page theme.
