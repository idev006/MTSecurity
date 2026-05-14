import { defineStore } from 'pinia'
import { ref } from 'vue'

export const ALL_THEMES = [
  'light', 'dark', 'cupcake', 'bumblebee', 'emerald', 'corporate',
  'synthwave', 'retro', 'cyberpunk', 'valentine', 'halloween', 'garden',
  'forest', 'aqua', 'lofi', 'pastel', 'fantasy', 'wireframe', 'black',
  'luxury', 'dracula', 'cmyk', 'autumn', 'business', 'acid', 'lemonade',
  'night', 'coffee', 'winter', 'dim', 'nord', 'sunset',
  'caramellatte', 'abyss', 'silk',
] as const

export type DaisyTheme = typeof ALL_THEMES[number]

const STORAGE_KEY = 'mt-theme'

function applyTheme(theme: string) {
  document.documentElement.setAttribute('data-theme', theme)
}

// Apply saved theme immediately (before Vue mounts) to prevent flash
const _saved = localStorage.getItem(STORAGE_KEY) ?? 'dark'
applyTheme(_saved)

export const useThemeStore = defineStore('theme', () => {
  const currentTheme = ref<string>(_saved)

  function setTheme(theme: string) {
    currentTheme.value = theme
    applyTheme(theme)
    localStorage.setItem(STORAGE_KEY, theme)
  }

  return { currentTheme, setTheme }
})
