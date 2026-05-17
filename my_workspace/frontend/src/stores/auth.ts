import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserRead } from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserRead | null>(null)
  const token = ref<string | null>(localStorage.getItem('access_token'))

  const isAuthenticated = computed(() => !!token.value)
  const username = computed(() => user.value?.username ?? '')
  const role = computed(() => user.value?.role ?? '')
  const userInitial = computed(() => username.value[0]?.toUpperCase() ?? '?')

  async function login(username: string, password: string) {
    const res = await authApi.login(username, password)
    token.value = res.access_token
    localStorage.setItem('access_token', res.access_token)
    localStorage.setItem('refresh_token', res.refresh_token)
    await fetchMe()
  }

  async function logout() {
    const refreshToken = localStorage.getItem('refresh_token') ?? undefined
    try { await authApi.logout(refreshToken) } catch { /* token may already be expired */ }
    token.value = null
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    // Tear down WebSocket and camera store
    const { useSystemStore } = await import('@/stores/system')
    useSystemStore().destroy()
    const { useCamerasStore } = await import('@/stores/cameras')
    useCamerasStore().reset()
  }

  async function fetchMe() {
    try {
      user.value = await authApi.me()
    } catch {
      user.value = null
    }
  }

  return { user, token, isAuthenticated, username, role, userInitial, login, logout, fetchMe }
})

