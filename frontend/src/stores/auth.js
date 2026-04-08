import { reactive, readonly } from 'vue'
import request from '@/api/request'
import { isLocalProfile } from '@/services/runtime'

const AUTH_KEY = 'polycrystal_auth'

// Local profile default user
const LOCAL_USER = {
  id: 1,
  username: 'localuser',
  displayName: 'Local Researcher',
  role: 'user',
  email: 'local@polycrystindex.local'
}

const LOCAL_PERMISSIONS = ['task:read', 'task:write', 'result:read', 'result:write']

const state = reactive({
  user: null,
  token: null,
  permissions: [],
  isAuthenticated: false
})

function loadFromStorage() {
  // Local profile: auto-authenticate as local user
  if (isLocalProfile()) {
    state.user = LOCAL_USER
    state.permissions = LOCAL_PERMISSIONS
    state.isAuthenticated = true
    return
  }
  
  try {
    const stored = localStorage.getItem(AUTH_KEY)
    if (stored) {
      const data = JSON.parse(stored)
      state.user = data.user
      state.token = data.token
      state.permissions = data.permissions || []
      state.isAuthenticated = true
    }
  } catch (e) {
    localStorage.removeItem(AUTH_KEY)
  }
}

function saveToStorage() {
  const data = { user: state.user, token: state.token, permissions: state.permissions }
  localStorage.setItem(AUTH_KEY, JSON.stringify(data))
}

function clearStorage() {
  localStorage.removeItem(AUTH_KEY)
}

export const useAuthStore = () => {
  loadFromStorage()

  const login = async (username, password) => {
    try {
      const response = await request.post('/auth/login', {
        username,
        password
      })
      
      if (response.success && response.data) {
        state.user = response.data.user
        state.token = response.data.token
        state.permissions = response.data.permissions || []
        state.isAuthenticated = true
        saveToStorage()
        return { success: true, user: response.data.user, permissions: state.permissions }
      }
      return { success: false, message: response.message || 'Login failed' }
    } catch (error) {
      return { success: false, message: error.response?.data?.message || 'Network error' }
    }
  }

  const register = async (payload) => {
    try {
      const response = await request.post('/auth/register', {
        username: payload.username,
        password: payload.password,
        school: payload.school,
        organization: payload.organization
      })
      
      if (response.success) {
        return { success: true, message: response.message }
      }
      return { success: false, message: response.message || 'Registration failed' }
    } catch (error) {
      return { success: false, message: error.response?.data?.message || 'Network error' }
    }
  }

  const logout = () => {
    // Logout is disabled in local profile
    if (isLocalProfile()) return
    
    state.user = null
    state.token = null
    state.permissions = []
    state.isAuthenticated = false
    clearStorage()
  }

  const checkAuth = () => {
    loadFromStorage()
    return state.isAuthenticated
  }

  const getUser = () => state.user

  const getToken = () => state.token

  const getPermissions = () => state.permissions

  const hasPermission = (permission) => {
    return state.permissions.includes(permission)
  }

  return {
    state: readonly(state),
    login,
    register,
    logout,
    checkAuth,
    getUser,
    getToken,
    getPermissions,
    hasPermission
  }
}
