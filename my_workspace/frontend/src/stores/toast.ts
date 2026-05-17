import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: number
  type: ToastType
  message: string
  title?: string
}

let _nextId = 1

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<Toast[]>([])

  function push(toast: Omit<Toast, 'id'>, durationMs = 5000) {
    const id = _nextId++
    toasts.value.push({ id, ...toast })
    setTimeout(() => remove(id), durationMs)
  }

  function remove(id: number) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  function success(title: string, message?: string) {
    push({ type: 'success', title, message: message ?? '' })
  }

  function error(title: string, message?: string) {
    push({ type: 'error', title, message: message ?? '' })
  }

  function warning(title: string, message?: string) {
    push({ type: 'warning', title, message: message ?? '' })
  }

  function info(title: string, message?: string) {
    push({ type: 'info', title, message: message ?? '' })
  }

  return { toasts, push, remove, success, error, warning, info }
})
