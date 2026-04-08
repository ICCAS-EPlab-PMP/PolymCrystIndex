import request from '@/api/request'

const API_PREFIX = '/admin'

const adminService = {
  async getAdminUsers() {
    const response = await request.get(`${API_PREFIX}/users`)
    if (response.success) {
      return response.data || []
    }
    throw new Error(response.message || 'Failed to fetch users')
  },

  async createAdminUser(payload) {
    const response = await request.post(`${API_PREFIX}/users`, {
      username: payload.username,
      password: payload.password,
      role: payload.role,
      displayName: payload.displayName,
      school: payload.school,
      organization: payload.organization,
      isApproved: payload.isApproved,
      runLimitOverride: payload.runLimitOverride,
      maxThreadsOverride: payload.maxThreadsOverride
    })
    if (!response.success) {
      throw new Error(response.message || 'Failed to create user')
    }
    return response
  },

  async updateAdminUser(userId, payload) {
    const response = await request.patch(`${API_PREFIX}/users/${userId}`, {
      role: payload.role,
      displayName: payload.displayName,
      school: payload.school,
      organization: payload.organization,
      isActive: payload.isActive,
      isApproved: payload.isApproved,
      runLimitOverride: payload.runLimitOverride,
      maxThreadsOverride: payload.maxThreadsOverride
    })
    if (!response.success) {
      throw new Error(response.message || 'Failed to update user')
    }
    return response
  },

  async disableAdminUser(userId) {
    const response = await request.post(`${API_PREFIX}/users/${userId}/disable`)
    if (!response.success) {
      throw new Error(response.message || 'Failed to disable user')
    }
    return response
  },

  async enableAdminUser(userId) {
    const response = await request.post(`${API_PREFIX}/users/${userId}/enable`)
    if (!response.success) {
      throw new Error(response.message || 'Failed to enable user')
    }
    return response
  },

  async getAdminTasks(params = {}) {
    const queryParams = new URLSearchParams()
    if (params.user_id) queryParams.append('user_id', params.user_id)
    if (params.status) queryParams.append('status', params.status)
    
    const query = queryParams.toString()
    const url = `${API_PREFIX}/tasks${query ? `?${query}` : ''}`
    const response = await request.get(url)
    if (response.success) {
      return response.data || []
    }
    throw new Error(response.message || 'Failed to fetch tasks')
  },

  async getAdminTaskDetail(taskId) {
    const response = await request.get(`${API_PREFIX}/tasks/${taskId}`)
    if (!response.success) {
      throw new Error(response.message || 'Failed to fetch task detail')
    }
    return response.data
  },

  async getAdminTaskLogs(taskId, mode = 'summary') {
    const response = await request.get(`${API_PREFIX}/tasks/${taskId}/logs?mode=${mode}`)
    if (!response.success) {
      throw new Error(response.message || 'Failed to fetch task logs')
    }
    return response.data?.logs || []
  },

  async cancelAdminTask(taskId) {
    const response = await request.post(`${API_PREFIX}/tasks/${taskId}/cancel`)
    if (!response.success) {
      throw new Error(response.message || 'Failed to cancel task')
    }
    return response
  },

  async getAdminSystemStatus() {
    const response = await request.get('/status')
    if (response.success) {
      return response.data
    }
    throw new Error(response.message || 'Failed to fetch system status')
  },

  async getHealthInfo() {
    const response = await request.get('/status/health')
    return response
  },

  async resetUserPassword(userId, newPassword) {
    const response = await request.post(`${API_PREFIX}/users/${userId}/reset-password`, {
      new_password: newPassword
    })
    if (!response.success) {
      throw new Error(response.message || 'Failed to reset password')
    }
    return response
  },

  async getDashboard() {
    const response = await request.get(`${API_PREFIX}/dashboard`)
    if (response.success) {
      return response.data
    }
    throw new Error(response.message || 'Failed to fetch dashboard')
  },

  async getRuntimeConfig() {
    const response = await request.get(`${API_PREFIX}/system/runtime-config`)
    if (response.success) {
      return response.data
    }
    throw new Error(response.message || 'Failed to fetch runtime config')
  },

  async updateRuntimeConfig(payload) {
    const response = await request.put(`${API_PREFIX}/system/runtime-config`, {
      maxJobs: payload.maxJobs,
      maxOmpThreads: payload.maxOmpThreads,
      defaultUserRunLimit: payload.defaultUserRunLimit,
      defaultUserMaxThreads: payload.defaultUserMaxThreads,
      approvedUserRunLimit: payload.approvedUserRunLimit,
      approvedUserMaxThreads: payload.approvedUserMaxThreads
    })
    if (!response.success) {
      throw new Error(response.message || 'Failed to update runtime config')
    }
    return response
  }
}

export default adminService
