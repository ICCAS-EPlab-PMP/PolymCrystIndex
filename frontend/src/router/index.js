import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { hasPermission } from '@/services/permission'
import { isLocalProfile, requiresAuth } from '@/services/runtime'
import userRoutes from './modules/user'
import adminRoutes from './modules/admin'

// Build dynamic routes based on profile
const buildRoutes = () => {
  const routes = []
  
  // Login route only for cloud profile
  if (!isLocalProfile()) {
    routes.push({ path: '/login', name: 'Login', component: () => import('@/views/Login.vue'), meta: { requiresAuth: false } })
  }
  
  // Add user routes for all profiles
  routes.push(...userRoutes)
  
  // Admin routes only for cloud profile
  if (!isLocalProfile()) {
    routes.push(...adminRoutes)
  }
  
  // Catch all route
  routes.push({ path: '/:pathMatch(.*)*', redirect: '/app/home' })
  
  return routes
}

const router = createRouter({
  history: createWebHistory(),
  routes: buildRoutes()
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const isAuthenticated = authStore.checkAuth()

  // Local profile: no auth required, skip all checks
  if (isLocalProfile()) {
    return next()
  }

  // Cloud profile auth checks
  if (to.meta.requiresAuth && !isAuthenticated) {
    next({ name: 'Login' })
  } else if (to.name === 'Login' && isAuthenticated) {
    next({ name: 'UserHome' })
  } else if (to.meta.requiresAdmin && !hasPermission('user:read')) {
    next({ name: 'UserHome' })
  } else {
    next()
  }
})

export default router
