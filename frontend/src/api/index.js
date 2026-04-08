import request from './request'

export const api = {
  async login(username, password) {
    return request.post('/auth/login', { username, password })
  },

  async register(username, password) {
    return request.post('/auth/register', { username, password })
  },

  async getMe() {
    return request.get('/auth/me')
  },

  async checkData(fileContent) {
    return request.post('/data/check', fileContent, {
      headers: { 'Content-Type': 'text/plain' }
    })
  },

  async uploadData(file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/data/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  async runAnalysis(dataFile, params) {
    return request.post('/analysis/run', {
      dataFile,
      params
    })
  },

  async getAnalysisStatus(taskId) {
    return request.get(`/analysis/status/${taskId}`)
  },

  async getAnalysisLogs(taskId, mode = 'summary') {
    return request.get(`/analysis/logs/${taskId}?mode=${mode}`)
  },

  async cancelAnalysis(taskId) {
    return request.post(`/analysis/cancel/${taskId}`)
  },

  async getResults() {
    return request.get('/results')
  },

  async downloadResults(type = 'zip', taskId = null) {
    const params = new URLSearchParams()
    params.append('type', type)
    if (taskId) params.append('task_id', taskId)
    
    const stored = localStorage.getItem('polycrystal_auth')
    const token = stored ? JSON.parse(stored).token : ''
    
    const response = await fetch(`/api/results/download?${params}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    if (!response.ok) {
      throw new Error('Download failed')
    }
    
    const blob = await response.blob()
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = `results.${type === 'zip' ? 'zip' : type}`
    if (contentDisposition) {
      const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (match) {
        filename = match[1].replace(/['"]/g, '')
      }
    }
    return { blob, filename }
  },

  async getServerStatus() {
    return request.get('/status')
  },

  async parsePoniFile(file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/visualizer/params', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  async getMillerData(taskId, type = 'full') {
    return request.get(`/visualizer/miller/${taskId}?miller_type=${type}`)
  },

  async getProcessingInfo(taskId) {
    return request.get(`/visualizer/processing-info/${taskId}`)
  },

  async getAvailableImages(taskId) {
    return request.get(`/visualizer/available-images/${taskId}`)
  },

  async getDiffractionImage(taskId, mode = 'raw') {
    const token = localStorage.getItem('token') || ''
    const response = await fetch(`/api/visualizer/image/${taskId}?mode=${mode}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })
    
    if (!response.ok) {
      throw new Error('Failed to download image')
    }
    
    const contentDisposition = response.headers.get('Content-Disposition')
    let filename = `image.${mode === 'raw' ? 'tif' : 'npy'}`
    if (contentDisposition) {
      const match = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
      if (match) {
        filename = match[1].replace(/['"]/g, '')
      }
    }
    
    return {
      blob: await response.blob(),
      filename
    }
  },

  async computePixels(millerData, params) {
    return request.post('/visualizer/compute-pixels', {
      millerData,
      params
    })
  },

  async uploadIntegrationData(file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/visualizer/integration2d', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  async parseDiffractionImage(file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/visualizer/parse-image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  async getVisualizerStatus() {
    return request.get('/visualizer/status')
  },

  async rawUploadImage(file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/visualizer/raw/upload-image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  async rawUploadPoni(file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/visualizer/raw/upload-poni', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  async rawUploadMiller(file, millerType = 'full') {
    const formData = new FormData()
    formData.append('file', file)
    return request.post(`/visualizer/raw/upload-miller?miller_type=${millerType}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  async rawClearMiller(millerType = 'all') {
    return request.delete(`/visualizer/raw/miller?miller_type=${millerType}`)
  },

  async rawRender(params) {
    return request.post('/visualizer/raw/render', params)
  },

  async rawImageOnly(params) {
    return request.post('/visualizer/raw/image-only', params)
  },

  async rawMarkers(params) {
    return request.post('/visualizer/raw/markers', params)
  },

  async intUploadImage(file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/visualizer/int/upload-image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  async intUploadInfo(file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/visualizer/int/upload-info', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  async intUploadMiller(file, millerType = 'full') {
    const formData = new FormData()
    formData.append('file', file)
    return request.post(`/visualizer/int/upload-miller?miller_type=${millerType}`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  async intClearMiller(millerType = 'all') {
    return request.delete(`/visualizer/int/miller?miller_type=${millerType}`)
  },

  async intUpdateRanges(body) {
    return request.put('/visualizer/int/coordinate-ranges', body)
  },

  async intRender(params) {
    return request.post('/visualizer/int/render', params)
  }
}

export default api