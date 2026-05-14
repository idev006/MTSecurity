# 18 — UI/UX Overhaul: Dynamic Theming & Toast System
### DaisyUI-Native Design · Theme Persistence · Browser-Dialog Elimination

---

## 0. บริบทและแรงจูงใจ

### ปัญหาที่แก้ไข

| # | ปัญหาเดิม | ผลกระทบ |
|---|-----------|---------|
| 1 | Theme switching ทำงานเฉพาะใน `SettingsView` — ถ้า user ไปหน้าอื่นก่อนจะยังเห็น theme ผิด | UX สับสน, flash of wrong theme |
| 2 | Theme list มีแค่ 8 รายการจาก 35 ธีมของ DaisyUI v5 | ขาด flexibility |
| 3 | `alert()` ใน `ZonesView.vue` (บรรทัด 333, 388) และ `confirm()` (บรรทัด 338) | native browser dialog ทำลาย theme, ไม่ accessible, ไม่ professional |
| 4 | Toast system ใน `AppLayout` รับ event จาก WebSocket เท่านั้น | component อื่นไม่สามารถ trigger toast ได้ |

### เป้าหมาย

```
1. Theme สมบูรณ์ทุกหน้า — ไม่มี flash
2. เลือก theme ได้จาก navbar ทุกหน้า — ไม่ต้องเข้า Settings
3. ไม่มี alert() / confirm() แม้แต่ครั้งเดียว
4. Toast ใช้ได้จาก component ใดก็ได้ผ่าน Pinia store
```

---

## 1. ไฟล์ที่สร้างใหม่

### 1.1 `src/stores/toast.ts` — Global Toast Store

**แนวคิด:** Pinia store เล็กๆ ที่ทำหน้าที่เป็น message bus สำหรับ UI notifications

```typescript
// Interface หลัก
export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: number
  type: ToastType
  message: string
  title?: string          // optional — ถ้ามีจะแสดงเป็น bold header
}

// การใช้งานจาก component ใดก็ได้
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()

// ตัวอย่าง
toast.push({ type: 'success', message: 'Zone saved successfully' })
toast.push({ type: 'error', title: 'Save Failed', message: 'Failed to save zone: ' + e.message })
toast.push({ type: 'warning', message: 'Connection unstable' })
toast.push({ type: 'info', message: 'Camera restarting…', durationMs: 8000 })
```

**Lifecycle:**
```
push() → เพิ่ม toast ใน array → setTimeout(durationMs) → remove(id) อัตโนมัติ
```

**default `durationMs` = 5000 ms** (override ได้ใน argument ที่ 2)

---

### 1.2 `src/stores/theme.ts` — Global Theme Store

**แนวคิด:** ใช้ module-level IIFE เพื่อ apply theme **ก่อน** Vue mount — ขจัด flash of wrong theme

```typescript
// รายชื่อ DaisyUI v5 ทั้ง 35 themes
export const ALL_THEMES = [
  'light', 'dark', 'cupcake', 'bumblebee', 'emerald', 'corporate',
  'synthwave', 'retro', 'cyberpunk', 'valentine', 'halloween', 'garden',
  'forest', 'aqua', 'lofi', 'pastel', 'fantasy', 'wireframe', 'black',
  'luxury', 'dracula', 'cmyk', 'autumn', 'business', 'acid', 'lemonade',
  'night', 'coffee', 'winter', 'dim', 'nord', 'sunset',
  'caramellatte', 'abyss', 'silk',
] as const
```

**กลไกสำคัญ — ไม่มี flash:**
```typescript
// บรรทัดนี้รันทันทีที่ module ถูก import (ก่อน Vue mount)
const _saved = localStorage.getItem('mt-theme') ?? 'dark'
applyTheme(_saved)   // ← sets document.documentElement.setAttribute('data-theme', ...)
```

**localStorage key:** `mt-theme` (เปลี่ยนจาก `theme` ของเดิม เพื่อ namespace ที่ชัดเจน)

**การใช้งาน:**
```typescript
import { useThemeStore, ALL_THEMES } from '@/stores/theme'

const themeStore = useThemeStore()

themeStore.currentTheme   // string — ชื่อ theme ปัจจุบัน
themeStore.setTheme('cyberpunk')  // apply + persist ทันที
```

---

## 2. ไฟล์ที่แก้ไข

### 2.1 `src/App.vue`

**เหตุผล:** root component ควร instantiate theme store เพื่อให้ Pinia register state ตั้งแต่แรก แม้ module-level IIFE apply ไปแล้ว

```typescript
// ก่อน (เดิม)
import { RouterView } from 'vue-router'

// หลัง (ใหม่)
import { RouterView } from 'vue-router'
import { useThemeStore } from '@/stores/theme'
useThemeStore()   // register Pinia state — ไม่ต้องทำอะไรเพิ่ม
```

---

### 2.2 `src/components/AppLayout.vue`

#### a) Theme Switcher Dropdown ใน Navbar

ตำแหน่ง: ระหว่าง RAM gauge และ Alert bell

```
[WS: LIVE] [CPU 12%] [RAM 34%] [🎨 dark ▾] [🔔] [👤]
```

**UX decisions:**
- แสดงบน `sm:` breakpoint ขึ้นไป (ซ่อนบน mobile เพื่อประหยัด space)
- ชื่อ theme แสดง uppercase จาก store — update ทันทีเมื่อเปลี่ยน
- Dropdown list เป็น `max-h-72 overflow-y-auto` (scroll ได้เพราะ 35 รายการ)
- แต่ละ item มี 3 จุดสี `bg-primary / bg-secondary / bg-accent` ด้วย `:data-theme="t"` isolation

**Color swatch pattern:**
```html
<!-- isolation ด้วย data-theme ทำให้จุดสีแสดงสีของ theme นั้น ไม่ใช่ theme ปัจจุบัน -->
<span :data-theme="t" class="inline-flex gap-0.5 shrink-0">
  <span class="w-2 h-2 rounded-full bg-primary"></span>
  <span class="w-2 h-2 rounded-full bg-secondary"></span>
  <span class="w-2 h-2 rounded-full bg-accent"></span>
</span>
```

#### b) Toast System — Dual Track

Toast container ใน AppLayout แสดง **2 แหล่ง** แยกจากกัน:

```
┌─────────────────────────────────────────┐
│ Toast Stack (bottom-right, z-[100])     │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │ 🔴 INTRUSION (CAM 2)  [WS alert] │  │ ← activeWsToasts (WebSocket)
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │ ✕ ❌ Save Failed  [programmatic] │  │ ← toastStore.toasts (Pinia)
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

**ไม่ merge กัน** เพื่อรักษา UX ที่ต่างกัน:
- WS toasts: คลิกไปหน้า Events, ไม่มี close button, dismiss อัตโนมัติ 6s
- Programmatic toasts: มี `✕` close button, dismiss อัตโนมัติ 5s, มี icon ตาม type

---

### 2.3 `src/views/ZonesView.vue`

#### การแทนที่ Browser Dialogs

| เดิม | ใหม่ | บรรทัด |
|------|------|--------|
| `alert('Failed to save zone: ' + e.message)` | `toastStore.push({ type: 'error', title: 'Save Failed', message: ... })` | 333 |
| `alert('Failed to save rule: ' + e.message)` | `toastStore.push({ type: 'error', title: 'Save Failed', message: ... })` | 388 |
| `confirm('Delete this zone and all its rules?')` | DaisyUI `<dialog>` modal | 338 |

#### Delete Zone Modal Flow

```
[Delete button click]
        │
        ▼
deleteZone(id)
  ├── deleteTargetZoneId.value = id
  └── deleteZoneModalOpen.value = true
        │
        ▼
  [Modal แสดง]
  ┌──────────────────────────────┐
  │ DELETE ZONE?                 │
  │ This zone and all its rules  │
  │ will be permanently removed. │
  │                              │
  │ [CANCEL]          [DELETE]   │
  └──────────────────────────────┘
        │                  │
        ▼                  ▼
   modal ปิด         confirmDeleteZone()
                       ├── reset modal state
                       ├── await apiDelete(...)
                       ├── zones.value = filter(...)
                       └── rules.value = filter(...)
```

**Reactive state ที่เพิ่ม:**
```typescript
const deleteZoneModalOpen = ref(false)
const deleteTargetZoneId  = ref<number | null>(null)
```

---

### 2.4 `src/views/SettingsView.vue` — DISPLAY Tab

#### ก่อน
- `themes` array แบบ hardcode 8 รายการ
- `currentTheme` ref แยก (ไม่ sync กับ global state)
- `setTheme()` function ซ้ำกับ store
- `onMounted` apply theme อีกครั้ง (redundant)

#### หลัง
- Import `useThemeStore` + `ALL_THEMES` จาก store — source of truth เดียว
- ตาราง theme 4 columns บน desktop แสดงครบ 35 รายการ
- แต่ละปุ่มมี 3 จุดสี `:data-theme` isolation (เหมือน dropdown ใน navbar)
- Preview row แสดง semantic badge ครบทุก variant

```
CONSOLE THEME                              [current: dim]
┌────────────────────────────────────────────────────────┐
│ [● ● ●] light  │ [● ● ●] dark   │ [● ● ●] cupcake    │ ...
│ [● ● ●] nord ✓ │ [● ● ●] sunset │ [● ● ●] abyss      │ ...
│ ...35 themes total...                                  │
├────────────────────────────────────────────────────────┤
│ PREVIEW — CURRENT THEME                                │
│ [ONLINE] [ALERT] [WARN] [INFO] [PRIMARY] [SECONDARY]  │
└────────────────────────────────────────────────────────┘
```

---

### 2.5 `src/style.css`

#### Smooth Theme Transitions

```css
*, *::before, *::after {
  transition:
    background-color 0.15s ease,
    border-color     0.15s ease,
    color            0.08s ease,
    box-shadow       0.15s ease;
}
```

**ทำไมไม่ใส่ `color` 0.15s?** — text color ที่ transition ช้าทำให้รู้สึก "lag" ระหว่างอ่าน, 0.08s เร็วพอที่ไม่สังเกต แต่ smooth กว่า instant

**ทำไมไม่ใส่ `all`?** — `all` รวม `transform`, `opacity`, `width` ฯลฯ ซึ่งจะทำลาย animation ของ component ที่มีอยู่แล้ว

#### Thin Custom Scrollbars

```css
::-webkit-scrollbar       { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: oklch(var(--bc) / 0.2); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: oklch(var(--bc) / 0.35); }
```

**`oklch(var(--bc) / 0.2)`** — ใช้ DaisyUI CSS variable `--bc` (base-content color) ทำให้ scrollbar ปรับตาม theme อัตโนมัติ ไม่ต้อง hardcode สี

---

## 3. สถาปัตยกรรม — ก่อนและหลัง

### Theme System

```
ก่อน (scattered):
┌─────────────────┐     ┌─────────────────┐
│  SettingsView   │     │   LoginView      │
│  currentTheme   │     │  (no theme init) │
│  setTheme()     │     └─────────────────┘
│  onMounted →    │
│  apply theme    │     ← theme ใช้ได้เฉพาะหลัง visit Settings
└─────────────────┘

หลัง (centralized):
┌──────────────────────────────────────────┐
│  stores/theme.ts                         │
│  ┌──────────────────────────────────┐   │
│  │ module IIFE (runs at import time) │   │
│  │ → reads localStorage             │   │
│  │ → sets data-theme on <html>      │   │
│  └──────────────────────────────────┘   │
│  useThemeStore() — currentTheme, setTheme│
└──────────────────┬───────────────────────┘
                   │ imported by
       ┌───────────┼───────────────┐
       ▼           ▼               ▼
   App.vue    AppLayout.vue   SettingsView.vue
   (init)    (navbar dropdown) (DISPLAY tab)
```

### Toast System

```
ก่อน:
  WebSocket alert → events.latestAlert → watch → activeToasts[] → render

หลัง:
  WebSocket alert → events.latestAlert → watch → activeWsToasts[]  ─┐
                                                                      ├→ render (dual track)
  Any component → toastStore.push() → toastStore.toasts[]          ─┘
```

---

## 4. Verification Checklist

```
Theme System:
□ เปิด browser ใหม่ → theme ที่เลือกไว้ยังอยู่ (ตรวจ localStorage['mt-theme'])
□ เปลี่ยน theme จาก navbar dropdown → ทุกหน้าเปลี่ยนทันที ไม่ต้องรีโหลด
□ เปิด Settings → Display → เห็น 35 themes พร้อม color swatches
□ คลิก theme ใน Settings → navbar dropdown แสดงชื่อใหม่ทันที (shared state)
□ Transition smooth เมื่อเปลี่ยน theme (0.15s ไม่กระตุก)

Toast System:
□ ไปหน้า Zones → จำลอง save error → toast ปรากฏ bottom-right (ไม่มี browser alert)
□ Toast มี title "Save Failed" และ message ของ error
□ Toast หายอัตโนมัติใน 5 วินาที
□ กด ✕ บน toast → หายทันที
□ WebSocket alert toast ยังทำงานเหมือนเดิม (คลิกไปหน้า Events)

Delete Zone Modal:
□ คลิก Delete บน zone → modal ปรากฏ (ไม่มี browser confirm)
□ กด CANCEL → modal ปิด zone ยังอยู่
□ กด DELETE → zone ถูกลบ modal ปิด
□ คลิก backdrop → modal ปิด (ยกเลิก)

Code Cleanliness:
□ grep ทุก .vue ไม่พบ alert( หรือ confirm(
```

---

## 5. การขยายในอนาคต

### เพิ่ม theme ใหม่

```typescript
// stores/theme.ts
export const ALL_THEMES = [
  ...existing,
  'my-custom-theme',  // เพิ่มที่นี่ที่เดียว
] as const
```

DaisyUI v5 ออก theme ใหม่ได้ตลอด — เพิ่มที่ array เดียว ทั้ง navbar dropdown และ Settings grid จะแสดงอัตโนมัติ

### เพิ่ม toast จาก component ใหม่

```typescript
// ใน component ใดก็ได้
import { useToastStore } from '@/stores/toast'
const toast = useToastStore()

// success
toast.push({ type: 'success', message: 'Camera added' })

// error with title
toast.push({ type: 'error', title: 'Connection Failed', message: err.message })

// warning พร้อม duration เอง
toast.push({ type: 'warning', message: 'High CPU usage' }, 10_000)
```

### เพิ่ม confirm modal แบบ reusable

ถ้ามี use case delete เพิ่มขึ้นอีก แนะนำสร้าง component กลาง:

```typescript
// components/ConfirmModal.vue
// props: open, title, message, confirmLabel, cancelLabel
// emits: confirm, cancel
```

แล้ว ZonesView และ component อื่นๆ ใช้ร่วมกัน — ลด boilerplate

---

## 6. Dependencies & Compatibility

| เทคโนโลยี | Version | หมายเหตุ |
|-----------|---------|---------|
| DaisyUI | v5.5.19 | ใช้ `data-theme` attribute บน `<html>` |
| Tailwind CSS | v4.3.0 | `oklch()` color space รองรับ |
| Vue | v3.5.32 | Composition API, `ref`, `watch` |
| Pinia | v3.0.4 | `defineStore` pattern |
| TypeScript | v6.0.2 | strict typing ทุก store |

**Browser compatibility:**
- `::-webkit-scrollbar` — Chrome/Edge/Safari (Firefox ใช้ `scrollbar-width: thin` แทน)
- `oklch()` — รองรับบน Chrome 111+, Firefox 113+, Safari 16.4+
- `data-theme` isolation บน color swatches — ทำงานถูกต้องบนทุก browser รุ่นใหม่

---

## 7. ไฟล์ที่แก้ไขสรุป

```
my_workspace/frontend/src/
├── App.vue                          ← เพิ่ม useThemeStore()
├── style.css                        ← เพิ่ม transitions + scrollbars
├── stores/
│   ├── toast.ts                     ← NEW: global toast store
│   └── theme.ts                     ← NEW: global theme store + ALL_THEMES
├── components/
│   └── AppLayout.vue                ← theme dropdown + dual-track toasts
└── views/
    ├── ZonesView.vue                ← replace alert()/confirm() → toast/modal
    └── SettingsView.vue             ← use theme store, 35 themes with swatches
```

---

*เอกสารนี้บันทึกโดย Claude Code — 2026-05-14*
*ส่วนหนึ่งของ MTSecurity v2 Architecture Documentation Series*
