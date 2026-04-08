import { useAuthStore } from '@/stores/auth'

const hasRole = (role) => {
  const authStore = useAuthStore()
  return authStore.state.user?.role === role
}

const hasPermission = (permission) => {
  const authStore = useAuthStore()
  return authStore.hasPermission(permission)
}

export { hasRole, hasPermission }
