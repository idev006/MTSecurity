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

  return { toasts, push, remove }
})
