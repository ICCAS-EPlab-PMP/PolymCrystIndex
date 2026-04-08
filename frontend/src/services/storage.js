import { isElectron } from './runtime'

const _storage = {
  getItem(key) {
    try {
      return localStorage.getItem(key)
    } catch {
      return null
    }
  },

  setItem(key, value) {
    try {
      localStorage.setItem(key, value)
    } catch {
      // storage full or unavailable
    }
  },

  removeItem(key) {
    try {
      localStorage.removeItem(key)
    } catch {
      // ignore
    }
  },

  getJSON(key) {
    try {
      const raw = this.getItem(key)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  },

  setJSON(key, value) {
    this.setItem(key, JSON.stringify(value))
  },
}

export const storage = {
  getItem: (key) => _storage.getItem(key),
  setItem: (key, value) => _storage.setItem(key, value),
  removeItem: (key) => _storage.removeItem(key),
  getJSON: (key) => _storage.getJSON(key),
  setJSON: (key, value) => _storage.setJSON(key, value),
}

export default storage
