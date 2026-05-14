<template>
  <div class="min-h-screen bg-base-200 bg-dot-grid flex items-center justify-center p-4">

    <div class="w-full max-w-sm flex flex-col items-center gap-4">

      <!-- Card -->
      <div class="card w-full glass-card shadow-2xl border-t-4 border-t-primary glow-primary-sm">
        <div class="card-body gap-5">

          <!-- Logo + Branding -->
          <div class="flex flex-col items-center gap-3 pt-2">
            <div class="w-16 h-16 bg-primary rounded-2xl flex items-center justify-center
                        shadow-lg ring-4 ring-primary/20 glow-primary">
              <svg class="h-9 w-9 text-primary-content" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8"
                  d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
              </svg>
            </div>
            <div class="text-center">
              <h1 class="text-2xl font-bold font-mono tracking-tight">MTSecurity</h1>
              <p class="text-xs opacity-40 font-mono tracking-widest mt-0.5">PILOT'S CONSOLE v2</p>
            </div>
          </div>

          <div class="divider my-0 opacity-30"></div>

          <!-- Form -->
          <form @submit.prevent="handleLogin" class="flex flex-col gap-4">

            <!-- Username -->
            <label class="form-control w-full">
              <div class="label pb-1">
                <span class="label-text font-mono text-xs font-bold tracking-widest opacity-50">USERNAME</span>
              </div>
              <input v-model="form.username" type="text" placeholder="operator"
                class="input input-bordered w-full font-mono"
                :class="errors.username ? 'input-error' : ''"
                autocomplete="username" required />
              <div v-if="errors.username" class="label pt-1">
                <span class="label-text-alt text-error font-mono">{{ errors.username }}</span>
              </div>
            </label>

            <!-- Password -->
            <label class="form-control w-full">
              <div class="label pb-1">
                <span class="label-text font-mono text-xs font-bold tracking-widest opacity-50">PASSWORD</span>
              </div>
              <div class="relative">
                <input v-model="form.password"
                  :type="showPassword ? 'text' : 'password'"
                  placeholder="••••••••"
                  class="input input-bordered w-full font-mono pr-10"
                  :class="errors.password ? 'input-error' : ''"
                  autocomplete="current-password" required />
                <!-- show/hide toggle -->
                <button type="button"
                  class="btn btn-ghost btn-xs btn-square absolute right-2 top-1/2 -translate-y-1/2 opacity-40 hover:opacity-80"
                  @click="showPassword = !showPassword"
                  :title="showPassword ? 'Hide password' : 'Show password'">
                  <!-- eye-off -->
                  <svg v-if="showPassword" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/>
                  </svg>
                  <!-- eye -->
                  <svg v-else class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                  </svg>
                </button>
              </div>
              <div v-if="errors.password" class="label pt-1">
                <span class="label-text-alt text-error font-mono">{{ errors.password }}</span>
              </div>
            </label>

            <!-- Login error -->
            <div v-if="loginError" class="alert alert-error py-2.5 text-sm font-mono">
              <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
              </svg>
              <span>{{ loginError }}</span>
            </div>

            <!-- Submit -->
            <button type="submit" class="btn btn-primary btn-lg w-full font-mono tracking-widest mt-1"
              :disabled="loading">
              <span v-if="loading" class="loading loading-spinner loading-sm"></span>
              <span>{{ loading ? 'AUTHENTICATING…' : 'SIGN IN' }}</span>
            </button>
          </form>

        </div>
      </div>

      <!-- Footer badge -->
      <div class="flex items-center gap-2 opacity-30">
        <span class="inline-block w-1.5 h-1.5 rounded-full bg-success animate-pulse"></span>
        <p class="text-xs font-mono tracking-widest">MTSecurity v2.0 · SECURE ACCESS PORTAL</p>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ApiError } from '@/api/client'

const router = useRouter()
const auth   = useAuthStore()

const form         = reactive({ username: '', password: '' })
const errors       = reactive({ username: '', password: '' })
const loginError   = ref('')
const loading      = ref(false)
const showPassword = ref(false)

async function handleLogin() {
  errors.username = ''
  errors.password = ''
  loginError.value = ''

  if (!form.username) { errors.username = 'Required'; return }
  if (!form.password) { errors.password = 'Required'; return }

  loading.value = true
  try {
    await auth.login(form.username, form.password)
    router.push('/dashboard')
  } catch (e) {
    loginError.value = e instanceof ApiError ? 'Invalid username or password' : 'Server error — try again'
  } finally {
    loading.value = false
  }
}
</script>
