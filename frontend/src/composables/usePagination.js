import { ref, computed } from 'vue'

export function usePagination(items, defaultPageSize = 20) {
  const currentPage = ref(1)
  const pageSize = ref(defaultPageSize)

  const totalPages = computed(() => {
    return Math.max(1, Math.ceil(items.value.length / pageSize.value))
  })

  const paginationStart = computed(() => {
    if (items.value.length === 0) return 0
    return (currentPage.value - 1) * pageSize.value + 1
  })

  const paginationEnd = computed(() => {
    const end = currentPage.value * pageSize.value
    return Math.min(end, items.value.length)
  })

  const paginatedItems = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value
    return items.value.slice(start, start + pageSize.value)
  })

  const visiblePages = computed(() => {
    const total = totalPages.value
    const current = currentPage.value
    if (total <= 7) {
      return Array.from({ length: total }, (_, i) => i + 1)
    }
    const pages = []
    if (current <= 4) {
      for (let i = 1; i <= 5; i++) pages.push(i)
      pages.push('...')
      pages.push(total)
    } else if (current >= total - 3) {
      pages.push(1)
      pages.push('...')
      for (let i = total - 4; i <= total; i++) pages.push(i)
    } else {
      pages.push(1)
      pages.push('...')
      for (let i = current - 1; i <= current + 1; i++) pages.push(i)
      pages.push('...')
      pages.push(total)
    }
    return pages
  })

  const resetPage = () => {
    currentPage.value = 1
  }

  return {
    currentPage,
    pageSize,
    totalPages,
    paginationStart,
    paginationEnd,
    paginatedItems,
    visiblePages,
    resetPage,
  }
}
