import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  { path: '/', redirect: '/pilot' },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/pilot',
    name: 'pilot',
    component: () => import('@/views/PilotView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/cameras',
    name: 'cameras',
    component: () => import('@/views/CamerasView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/events',
    name: 'events',
    component: () => import('@/views/EventsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/zones',
    name: 'zones',
    component: () => import('@/views/ZonesView.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/users',
    name: 'users',
    component: () => import('@/views/UsersView.vue'),
    meta: { requiresAuth: true, roles: ['SUPERADMIN', 'ADMIN'] },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const token = localStorage.getItem('access_token')
  if (to.meta.requiresAuth && !token) return { name: 'login' }
  if (to.name === 'login' && token)   return { name: 'dashboard' }

  // Hydrate auth.user whenever token exists but user is not in memory.
  // This covers page-refresh: token survives in localStorage but the
  // in-memory user ref resets to null, causing role-dependent UI to break.
  if (token && to.meta.requiresAuth) {
    const { useAuthStore } = await import('@/stores/auth')
    const auth = useAuthStore()
    if (!auth.user) await auth.fetchMe()

    // Role guard: redirect to dashboard if role not allowed
    const allowedRoles = to.meta.roles as string[] | undefined
    if (allowedRoles && !allowedRoles.includes(auth.role)) {
      return { name: 'dashboard' }
    }
  }
})

export default router
