import { ref, computed } from 'vue'

export interface ServerTableOptions {
  defaultPageSize?: number
  pageSizeOptions?: number[]
}

export function useServerTable(options: ServerTableOptions = {}) {
  const pageSizeOptions = options.pageSizeOptions ?? [10, 25, 50, 100]
  const page = ref(1)
  const pageSize = ref(options.defaultPageSize ?? 25)
  const total = ref<number | null>(null)

  const totalPages = computed(() =>
    total.value !== null ? Math.ceil(total.value / pageSize.value) : null
  )
  // Nullable override: true/false forces hasNext; null = auto-compute
  const hasNextOverride = ref<boolean | null>(null)

  const hasNext = computed(() => {
    if (hasNextOverride.value !== null) return hasNextOverride.value
    if (total.value !== null) return page.value < (totalPages.value ?? 1)
    return true
  })
  const hasPrev = computed(() => page.value > 1)

  function setPageSize(size: number) {
    pageSize.value = size
    page.value = 1
  }

  function nextPage(load: () => void) {
    if (hasNext.value) { page.value++; load() }
  }

  function prevPage(load: () => void) {
    if (hasPrev.value) { page.value--; load() }
  }

  function reset() {
    page.value = 1
    total.value = null
    hasNextOverride.value = null
  }

  return {
    page, pageSize, total, totalPages,
    hasNext, hasPrev, hasNextOverride, pageSizeOptions,
    setPageSize, nextPage, prevPage, reset,
  }
}
