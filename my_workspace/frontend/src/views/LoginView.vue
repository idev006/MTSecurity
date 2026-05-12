<template>
  <div class="min-h-screen bg-base-200 flex items-center justify-center p-4">
    <div class="card w-full max-w-sm bg-base-100 shadow-xl">
      <div class="card-body gap-6">
        <!-- Logo -->
        <div class="flex flex-col items-center gap-3 mb-2">
          <div class="w-14 h-14 bg-primary rounded-2xl flex items-center justify-center">
            <svg class="h-8 w-8 text-primary-content" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"/>
            </svg>
          </div>
          <div class="text-center">
            <h1 class="text-2xl font-bold font-mono">MTSecurity</h1>
            <p class="text-sm opacity-50 font-mono">PILOT'S CONSOLE v2</p>
          </div>
        </div>

        <!-- Form -->
        <form @submit.prevent="handleLogin" class="flex flex-col gap-4">
          <label class="form-control w-full">
            <div class="label"><span class="label-text font-mono text-xs opacity-60">USERNAME</span></div>
            <input v-model="form.username" type="text" placeholder="username"
              class="input input-bordered w-full font-mono"
              :class="{ 'input-error': errors.username }"
              autocomplete="username" required />
            <div v-if="errors.username" class="label">
              <span class="label-text-alt text-error">{{ errors.username }}</span>
            </div>
          </label>

          <label class="form-control w-full">
            <div class="label"><span class="label-text font-mono text-xs opacity-60">PASSWORD</span></div>
            <input v-model="form.password" type="password" placeholder="••••••••"
              class="input input-bordered w-full font-mono"
              :class="{ 'input-error': errors.password }"
              autocomplete="current-password" required />
            <div v-if="errors.password" class="label">
              <span class="label-text-alt text-error">{{ errors.password }}</span>
            </div>
          </label>

          <div v-if="loginError" role="alert" class="alert alert-error py-2 text-sm font-mono">
            <svg class="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
            <span>{{ loginError }}</span>
          </div>

          <button type="submit" class="btn btn-primary w-full font-mono" :disabled="loading">
            <span v-if="loading" class="loading loading-spinner loading-sm"></span>
            {{ loading ? 'AUTHENTICATING…' : 'SIGN IN' }}
          </button>
        </form>

        <p class="text-center text-xs opacity-30 font-mono">MTSecurity v2.0 · SECURE ACCESS</p>
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

const form       = reactive({ username: '', password: '' })
const errors     = reactive({ username: '', password: '' })
const loginError = ref('')
const loading    = ref(false)

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
