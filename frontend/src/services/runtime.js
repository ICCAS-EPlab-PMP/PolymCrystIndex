export const isElectron = () => !!(window && window.electronAPI)

// Get current active profile
export const getProfile = () => {
  // Priority: 1. Explicit environment variable
  const envProfile = import.meta.env.VITE_APP_PROFILE
  if (envProfile) return envProfile
  
  // 2. Electron context = local profile
  if (isElectron()) return 'local'
  
  // 3. Default to cloud
  return 'cloud'
}

// Check if current profile is local
export const isLocalProfile = () => getProfile() === 'local'

// Check if current profile is cloud
export const isCloudProfile = () => getProfile() === 'cloud'

// Check if authentication is required
export const requiresAuth = () => {
  // Local profile never requires auth
  if (isLocalProfile()) return false
  
  // Check legacy auth disabled flag for compatibility
  if (import.meta.env.VITE_AUTH_DISABLED === 'true') return false
  
  // Cloud profile requires auth by default
  return true
}

export const getApiBase = () => {
  // Local profile always uses localhost
  if (isLocalProfile()) return 'http://localhost:8000/api'
  
  // Cloud profile uses env config or relative path
  const envBase = import.meta.env.VITE_API_BASE_URL
  if (envBase) return envBase
  return '/api'
}

export const getRuntimeInfo = () => ({
  isElectron: isElectron(),
  profile: getProfile(),
  isLocal: isLocalProfile(),
  isCloud: isCloudProfile(),
  apiBase: getApiBase(),
  requiresAuth: requiresAuth(),
})

