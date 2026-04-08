import { ref, onUnmounted } from 'vue'

export function useAutoRefresh(loadFn, intervalMs = 15000) {
  const autoRefresh = ref(false)
  const refreshInterval = ref(null)
  const refreshing = ref(false)

  const toggleAutoRefresh = () => {
    if (autoRefresh.value) {
      autoRefresh.value = false
      if (refreshInterval.value) {
        clearInterval(refreshInterval.value)
        refreshInterval.value = null
      }
    } else {
      autoRefresh.value = true
      refreshInterval.value = setInterval(async () => {
        if (refreshing.value) return
        refreshing.value = true
        try {
          await loadFn()
        } finally {
          refreshing.value = false
        }
      }, intervalMs)
    }
  }

  onUnmounted(() => {
    if (refreshInterval.value) {
      clearInterval(refreshInterval.value)
      refreshInterval.value = null
    }
  })

  return {
    autoRefresh,
    refreshing,
    toggleAutoRefresh,
  }
}
