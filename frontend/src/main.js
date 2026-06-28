import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import './styles/global.css'

const app = createApp(App)

// ── Global Vue error handler ──────────────────────────────────────────
// Catches rendering errors that would otherwise show as a blank page.
// The error, component name, and lifecycle info are logged to console.
app.config.errorHandler = (err, vm, info) => {
  const name = vm?.$options?.__name || vm?.$options?.name || 'unknown'
  const msg = `[Vue Error] ${err && err.message ? err.message : err}\nComponent: ${name}\nInfo: ${info}`
  console.error('[Vue Render Error]', err, '\n  Component:', name, '\n  Info:', info)
  try {
    const banner = document.createElement('div')
    banner.style.cssText = 'position:fixed;top:0;left:0;right:0;padding:12px 16px;background:#dc2626;color:#fff;font-family:monospace;font-size:13px;z-index:999999;white-space:pre-wrap;max-height:40vh;overflow:auto;box-shadow:0 2px 8px rgba(0,0,0,.3)'
    banner.textContent = msg
    document.body.appendChild(banner)
  } catch (e) { /* ignore */ }
}

// ── window.$toast — minimal toast implementation ─────────────────────
// Provides user-visible feedback for async operations (file import,
// API calls, etc.). Many components call `window.$toast?.(msg, isError)`
// but it was never defined, causing all feedback (including errors) to
// be silently swallowed.
let _toastContainer = null
function _ensureToastContainer() {
  if (_toastContainer && document.body.contains(_toastContainer)) return _toastContainer
  _toastContainer = document.createElement('div')
  _toastContainer.id = 'app-toast-container'
  _toastContainer.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:99999;display:flex;flex-direction:column;gap:8px;pointer-events:none;'
  document.body.appendChild(_toastContainer)
  return _toastContainer
}
window.$toast = (message, isError = false) => {
  if (isError) console.error('[Toast ERROR]', message)
  else console.log('[Toast]', message)
  try {
    const container = _ensureToastContainer()
    const toast = document.createElement('div')
    toast.style.cssText = `pointer-events:auto;padding:10px 20px;border-radius:8px;color:#fff;font-size:14px;font-family:inherit;max-width:420px;box-shadow:0 4px 12px rgba(0,0,0,.25);opacity:0;transition:opacity .3s ease;${isError ? 'background:#dc2626' : 'background:#1e40af'}`
    toast.textContent = String(message)
    container.appendChild(toast)
    requestAnimationFrame(() => { toast.style.opacity = '1' })
    setTimeout(() => {
      toast.style.opacity = '0'
      setTimeout(() => toast.remove(), 300)
    }, 4000)
  } catch (e) { /* DOM not ready */ }
}

app.use(router)
app.use(i18n)
app.mount('#app')
