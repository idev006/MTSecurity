import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { eventsApi, type EventRead } from '@/api/client'

export const useEventsStore = defineStore('events', () => {
  const events = ref<EventRead[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const newCount = computed(() => events.value.filter(e => e.status === 'NEW').length)
  const recentAlerts = computed(() => events.value.slice(0, 10))

  async function fetchRecent(params?: Record<string, string | number>) {
    loading.value = true
    error.value = null
    try {
      const page = await eventsApi.list(params ?? { page_size: 50 })
      events.value = page.items
    } catch (e: any) {
      error.value = e.message
    } finally {
      loading.value = false
    }
  }

  const latestAlert = ref<EventRead | null>(null)

  function prependAlert(event: EventRead) {
    events.value = [event, ...events.value].slice(0, 200)
    latestAlert.value = event
  }

  async function acknowledge(id: number, note?: string) {
    await eventsApi.acknowledge(id, note)
    const ev = events.value.find(e => e.id === id)
    if (ev) ev.status = 'ACKNOWLEDGED'
  }

  async function ackAll() {
    const newEvents = events.value.filter(e => e.status === 'NEW')
    await Promise.all(newEvents.map(e => acknowledge(e.id)))
  }

  async function silence(id: number, duration_seconds = 300) {
    await eventsApi.silence(id, duration_seconds)
    const ev = events.value.find(e => e.id === id)
    if (ev) ev.status = 'SILENCED'
  }

  async function escalate(id: number, reason: string) {
    await eventsApi.escalate(id, reason)
    const ev = events.value.find(e => e.id === id)
    if (ev) ev.status = 'ESCALATED'
  }

  function remove(id: number) {
    events.value = events.value.filter(e => e.id !== id)
  }

  async function fetch() {
    return fetchRecent()
  }

  return {
    events, loading, error, newCount, recentAlerts, latestAlert,
    fetchRecent, fetch, prependAlert, acknowledge, ackAll, silence, escalate, remove,
  }
})
