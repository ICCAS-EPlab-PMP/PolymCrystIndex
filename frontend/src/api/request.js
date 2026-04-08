import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000
})

request.interceptors.request.use(
  config => {
    const authStore = useAuthStore()
    const token = authStore.getToken()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

request.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      const authStore = useAuthStore()
      authStore.logout()
      window.location.href = '/login'
    }
    const message = error.response?.data?.detail
      || error.response?.data?.message
      || error.message
    error.message = message
    return Promise.reject(error)
  }
)

export default request
