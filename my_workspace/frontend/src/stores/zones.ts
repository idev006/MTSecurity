import { defineStore } from 'pinia'
import { ref } from 'vue'
import { zonesApi, rulesApi, type ZoneRead, type RuleRead } from '@/api/client'

export const useZonesStore = defineStore('zones', () => {
  const zones = ref<ZoneRead[]>([])
  const rules = ref<RuleRead[]>([])
  const loading = ref(false)

  async function fetchAll() {
    loading.value = true
    try {
      const [z, r] = await Promise.all([
        zonesApi.list(),
        rulesApi.list(),
      ])
      zones.value = z
      rules.value = r
    } catch (e) {
      console.error('Failed to fetch zones/rules', e)
    } finally {
      loading.value = false
    }
  }

  function zonesForCamera(cameraId: number) {
    return zones.value.filter(z => z.camera_id === cameraId)
  }

  function rulesForZone(zoneId: number) {
    return rules.value.filter(r => r.zone_id === zoneId)
  }

  return {
    zones,
    rules,
    loading,
    fetchAll,
    zonesForCamera,
    rulesForZone,
  }
})
