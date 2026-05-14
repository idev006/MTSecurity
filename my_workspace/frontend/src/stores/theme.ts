/**
 * Theme store — manages DaisyUI theme selection.
 * Persists the chosen theme to localStorage and applies it to <html data-theme>.
 * Single source of truth; avoids duplicated theme logic across views.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

// All 35 DaisyUI v5 built-in themes
export const DAISY_THEMES = [
  'light', 'dark', 'cupcake', 'bumblebee', 'emerald', 'corporate',
  'synthwave', 'retro', 'cyberpunk', 'valentine', 'halloween', 'garden',
  'forest', 'aqua', 'lofi', 'pastel', 'fantasy', 'wireframe', 'black',
  'luxury', 'dracula', 'cmyk', 'autumn', 'business', 'acid', 'lemonade',
  'night', 'coffee', 'winter', 'dim', 'nord', 'sunset',
  'caramellatte', 'abyss', 'silk',
] as const

export type DaisyTheme = typeof DAISY_THEMES[number]

const STORAGE_KEY = 'mtsec_theme'
const DEFAULT_THEME: DaisyTheme = 'dark'

export const useThemeStore = defineStore('theme', () => {
  const current = ref<DaisyTheme>(
    (localStorage.getItem(STORAGE_KEY) as DaisyTheme | null) ?? DEFAULT_THEME,
  )

  const isDark = computed(() =>
    ['dark', 'synthwave', 'halloween', 'forest', 'black', 'luxury', 'dracula',
      'night', 'coffee', 'dim', 'sunset', 'abyss', 'cyberpunk'].includes(current.value),
  )

  /** Apply a theme immediately and persist it. */
  function setTheme(theme: DaisyTheme) {
    current.value = theme
    localStorage.setItem(STORAGE_KEY, theme)
    _apply(theme)
  }

  /** Restore from localStorage on app boot. */
  function init() {
    _apply(current.value)
  }

  function _apply(theme: DaisyTheme) {
    document.documentElement.setAttribute('data-theme', theme)
  }

  return { current, isDark, themes: DAISY_THEMES, setTheme, init }
})
