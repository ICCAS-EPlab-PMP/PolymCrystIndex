<template>
  <div class="system-status-page">
    <div class="page-header">
      <div class="header-content">
        <h1>{{ t('admin.system') }}</h1>
        <p class="description">{{ t('admin.systemDesc') }}</p>
      </div>
      <div class="header-actions">
        <button
          class="btn-toggle"
          :class="{ active: autoRefresh }"
          @click="toggleAutoRefresh"
        >
          <svg v-if="autoRefresh" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <path d="M5 12h14"/>
            <path d="M12 5l7 7-7 7"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polyline points="23 4 23 10 17 10"/>
            <polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
          </svg>
          {{ t('admin.autoRefresh') }}
        </button>
        <button class="btn-secondary" @click="loadStatus" :disabled="loading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6M1 20v-6h6"/>
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
          </svg>
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <div v-if="loading && !statusData" class="loading-state">
      <div class="spinner"></div>
      <p>{{ t('common.loading') }}</p>
    </div>

    <div v-else-if="error && !statusData" class="error-state">
      <p>{{ error }}</p>
      <button class="btn-secondary" @click="loadStatus">{{ t('common.retry') }}</button>
    </div>

    <template v-else>
      <div v-if="error && statusData" class="error-banner">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
          <circle cx="12" cy="12" r="10"/>
          <line x1="15" y1="9" x2="9" y2="15"/>
          <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
        <span>{{ error }}</span>
        <button class="banner-dismiss" @click="error = ''">&times;</button>
      </div>
      <div class="status-cards">
        <div class="status-card">
          <div class="card-icon cpu-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="4" y="4" width="16" height="16" rx="2" ry="2"/>
              <rect x="9" y="9" width="6" height="6"/>
              <line x1="9" y1="1" x2="9" y2="4"/>
              <line x1="15" y1="1" x2="15" y2="4"/>
              <line x1="9" y1="20" x2="9" y2="23"/>
              <line x1="15" y1="20" x2="15" y2="23"/>
              <line x1="20" y1="9" x2="23" y2="9"/>
              <line x1="20" y1="14" x2="23" y2="14"/>
              <line x1="1" y1="9" x2="4" y2="9"/>
              <line x1="1" y1="14" x2="4" y2="14"/>
            </svg>
          </div>
          <div class="card-content">
            <span class="card-label">{{ t('admin.cpuUsage') }}</span>
            <span class="card-value">{{ statusData?.cpuPercent?.toFixed(1) || 0 }}%</span>
          </div>
          <div class="card-bar">
            <div
              class="bar-fill cpu-bar"
              :style="{ width: `${statusData?.cpuPercent || 0}%` }"
            ></div>
          </div>
        </div>

        <div class="status-card">
          <div class="card-icon jobs-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/>
            </svg>
          </div>
          <div class="card-content">
            <span class="card-label">{{ t('admin.activeJobs') }}</span>
            <span class="card-value">{{ statusData?.activeJobs || 0 }} / {{ statusData?.maxJobs || 0 }}</span>
          </div>
          <div class="card-bar">
            <div
              class="bar-fill jobs-bar"
              :style="{ width: `${statusData?.maxJobs ? (statusData.activeJobs / statusData.maxJobs) * 100 : 0}%` }"
            ></div>
          </div>
        </div>

        <div class="status-card">
          <div class="card-icon memory-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="6" width="20" height="12" rx="2"/>
              <line x1="6" y1="6" x2="6" y2="18"/>
              <line x1="10" y1="6" x2="10" y2="18"/>
              <line x1="14" y1="6" x2="14" y2="18"/>
              <line x1="18" y1="6" x2="18" y2="18"/>
            </svg>
          </div>
          <div class="card-content">
            <span class="card-label">{{ t('admin.memoryUsage') }}</span>
            <span class="card-value">{{ statusData?.memoryPercent?.toFixed(1) || 0 }}%</span>
            <span class="card-detail">{{ statusData?.memoryUsed || 0 }} / {{ statusData?.memoryTotal || 0 }} GB</span>
          </div>
          <div class="card-bar">
            <div
              class="bar-fill memory-bar"
              :style="{ width: `${statusData?.memoryPercent || 0}%` }"
            ></div>
          </div>
        </div>

        <div class="status-card">
          <div class="card-icon disk-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <ellipse cx="12" cy="5" rx="9" ry="3"/>
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/>
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
            </svg>
          </div>
          <div class="card-content">
            <span class="card-label">{{ t('admin.diskUsage') }}</span>
            <span class="card-value">{{ statusData?.diskPercent?.toFixed(1) || 0 }}%</span>
            <span class="card-detail">{{ statusData?.diskUsed || 0 }} / {{ statusData?.diskTotal || 0 }} GB</span>
          </div>
          <div class="card-bar">
            <div
              class="bar-fill disk-bar"
              :style="{ width: `${statusData?.diskPercent || 0}%` }"
            ></div>
          </div>
        </div>

        <div class="status-card status-card-wide">
          <div class="card-icon service-icon" :class="statusClass">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path v-if="statusData?.status === 'idle'" d="M8 12l2 2 4-4"/>
              <path v-else-if="statusData?.status === 'busy'" d="M12 8v4l3 3"/>
              <path v-else d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3M12 17h.01"/>
            </svg>
          </div>
          <div class="card-content">
            <span class="card-label">{{ t('admin.serviceStatus') }}</span>
            <span class="card-value" :class="statusClass">{{ statusLabel }}</span>
          </div>
        </div>
      </div>

      <div class="info-section">
        <h2>{{ t('admin.systemInfo') }}</h2>
        <div class="info-grid">
          <div class="info-item">
            <span class="info-label">{{ t('admin.platform') }}</span>
            <span class="info-value">{{ statusData?.platform || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('admin.pythonVersion') }}</span>
            <span class="info-value">{{ statusData?.pythonVersion || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">{{ t('admin.version') }}</span>
            <span class="info-value">{{ versionInfo?.version || '-' }}</span>
          </div>
        </div>
      </div>

      <div class="config-section">
        <h2>{{ t('admin.runtimeConfig') }}</h2>
        <div v-if="configLoading" class="loading-inline">{{ t('common.loading') }}</div>
        <div v-else class="config-form">
          <div class="config-row">
            <div class="config-field">
              <label>{{ t('admin.maxJobs') }}</label>
              <input
                type="number"
                v-model.number="runtimeConfig.maxJobs"
                min="1"
                max="32"
                class="config-input"
              />
            </div>
            <div class="config-field">
              <label>{{ t('admin.maxOmpThreads') }}</label>
              <input
                type="number"
                v-model.number="runtimeConfig.maxOmpThreads"
                min="1"
                max="128"
                class="config-input"
              />
            </div>
          </div>
          <div class="config-row">
            <div class="config-field">
              <label>{{ t('admin.defaultUserRunLimit') }}</label>
              <input
                type="number"
                v-model.number="runtimeConfig.defaultUserRunLimit"
                min="0"
                class="config-input"
              />
            </div>
            <div class="config-field">
              <label>{{ t('admin.defaultUserMaxThreads') }}</label>
              <input
                type="number"
                v-model.number="runtimeConfig.defaultUserMaxThreads"
                min="1"
                :max="runtimeConfig.maxOmpThreads || 128"
                class="config-input"
              />
            </div>
          </div>
          <div class="config-row">
            <div class="config-field">
              <label>{{ t('admin.approvedUserRunLimit') }}</label>
              <input
                type="number"
                v-model.number="runtimeConfig.approvedUserRunLimit"
                min="0"
                class="config-input"
              />
            </div>
            <div class="config-field">
              <label>{{ t('admin.approvedUserMaxThreads') }}</label>
              <input
                type="number"
                v-model.number="runtimeConfig.approvedUserMaxThreads"
                min="1"
                :max="runtimeConfig.maxOmpThreads || 128"
                class="config-input"
              />
            </div>
          </div>
          <div class="config-actions">
            <button class="btn-primary" @click="saveRuntimeConfig" :disabled="configSaving">
              {{ configSaving ? t('common.loading') : t('admin.saveConfig') }}
            </button>
            <span v-if="configSuccess" class="config-success">{{ configSuccess }}</span>
            <span v-if="configError" class="config-error">{{ configError }}</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import adminService from '@/services/admin'

const { t } = useI18n()

const statusData = ref(null)
const versionInfo = ref(null)
const loading = ref(false)
const refreshing = ref(false)
const error = ref('')
const autoRefresh = ref(false)
const refreshInterval = ref(null)
const REFRESH_INTERVAL_MS = 15000
const runtimeConfig = ref({
  maxJobs: 1,
  maxOmpThreads: 1,
  defaultUserRunLimit: 30,
  defaultUserMaxThreads: 4,
  approvedUserRunLimit: 0,
  approvedUserMaxThreads: 1,
})
const configLoading = ref(false)
const configSaving = ref(false)
const configSuccess = ref('')
const configError = ref('')

const statusClass = computed(() => {
  const s = statusData.value?.status
  if (s === 'idle') return 'status-idle'
  if (s === 'busy') return 'status-busy'
  if (s === 'full') return 'status-full'
  return ''
})

const statusLabel = computed(() => {
  const s = statusData.value?.status
  if (s === 'idle') return t('admin.systemIdle')
  if (s === 'busy') return t('admin.systemBusy')
  if (s === 'full') return t('admin.systemFull')
  return '-'
})

const loadStatus = async (fromAutoRefresh = false) => {
  if (refreshing.value) return
  if (fromAutoRefresh) refreshing.value = true
  loading.value = !fromAutoRefresh
  error.value = ''
  try {
    const [status, health] = await Promise.all([
      adminService.getAdminSystemStatus(),
      adminService.getHealthInfo().catch(() => null)
    ])
    statusData.value = status
    versionInfo.value = health || null
  } catch (e) {
    error.value = e.message || t('admin.loadStatusError')
  } finally {
    loading.value = false
    refreshing.value = false
  }
}

const loadRuntimeConfig = async () => {
  configLoading.value = true
  configError.value = ''
  try {
    const data = await adminService.getRuntimeConfig()
    runtimeConfig.value = {
      maxJobs: data.maxJobs,
      maxOmpThreads: data.maxOmpThreads,
      defaultUserRunLimit: data.defaultUserRunLimit,
      defaultUserMaxThreads: data.defaultUserMaxThreads,
      approvedUserRunLimit: data.approvedUserRunLimit,
      approvedUserMaxThreads: data.approvedUserMaxThreads,
    }
  } catch (e) {
    configError.value = e.message || t('admin.configSaveFailed')
  } finally {
    configLoading.value = false
  }
}

const toggleAutoRefresh = () => {
  if (autoRefresh.value) {
    autoRefresh.value = false
    if (refreshInterval.value) {
      clearInterval(refreshInterval.value)
      refreshInterval.value = null
    }
  } else {
    autoRefresh.value = true
    refreshInterval.value = setInterval(() => loadStatus(true), REFRESH_INTERVAL_MS)
  }
}

const saveRuntimeConfig = async () => {
  configSaving.value = true
  configSuccess.value = ''
  configError.value = ''
  try {
    await adminService.updateRuntimeConfig({
      maxJobs: runtimeConfig.value.maxJobs,
      maxOmpThreads: runtimeConfig.value.maxOmpThreads,
      defaultUserRunLimit: runtimeConfig.value.defaultUserRunLimit,
      defaultUserMaxThreads: runtimeConfig.value.defaultUserMaxThreads,
      approvedUserRunLimit: runtimeConfig.value.approvedUserRunLimit,
      approvedUserMaxThreads: runtimeConfig.value.approvedUserMaxThreads,
    })
    configSuccess.value = t('admin.configSaved')
    setTimeout(() => { configSuccess.value = '' }, 3000)
  } catch (e) {
    configError.value = e.message || t('admin.configSaveFailed')
  } finally {
    configSaving.value = false
  }
}

onMounted(() => {
  loadStatus()
  loadRuntimeConfig()
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
    refreshInterval.value = null
  }
})
</script>

<style scoped>
.system-status-page {
  max-width: 900px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
  gap: 24px;
}

.header-content h1 {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.header-content .description {
  color: var(--text-secondary);
  font-size: 0.9375rem;
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-shrink: 0;
}

.btn-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid var(--border);
  background: var(--bg-surface);
  color: var(--text-secondary);
}

.btn-toggle.active {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.btn-toggle svg {
  width: 16px;
  height: 16px;
}

.btn-secondary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: none;
  background: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--border);
}

.btn-secondary:hover {
  background: var(--bg-surface-alt);
  color: var(--text-primary);
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary svg {
  width: 18px;
  height: 18px;
}

.loading-state, .error-state {
  text-align: center;
  padding: 64px;
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state {
  color: var(--error);
}

.error-state p {
  margin-bottom: 16px;
}

.error-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: var(--radius-md);
  color: var(--error);
  font-size: 0.875rem;
  margin-bottom: 20px;
}

.banner-dismiss {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--error);
  font-size: 1.25rem;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}

.status-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-bottom: 32px;
}

.status-card {
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  padding: 24px;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.status-card-wide {
  grid-column: span 2;
  flex-direction: row;
  align-items: center;
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.card-icon svg {
  width: 24px;
  height: 24px;
}

.cpu-icon {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.jobs-icon {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.memory-icon {
  background: rgba(168, 85, 247, 0.15);
  color: #a855f7;
}

.disk-icon {
  background: rgba(249, 115, 22, 0.15);
  color: #f97316;
}

.service-icon {
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
}

.service-icon.status-idle {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.service-icon.status-busy {
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
}

.service-icon.status-full {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.card-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
}

.card-detail {
  font-size: 0.8125rem;
  color: var(--text-muted);
  font-family: 'Fira Code', monospace;
}

.card-value.status-idle {
  color: #10b981;
}

.card-value.status-busy {
  color: #eab308;
}

.card-value.status-full {
  color: #ef4444;
}

.card-bar {
  height: 6px;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: var(--radius-full);
  transition: width 0.5s ease;
}

.cpu-bar {
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
}

.jobs-bar {
  background: linear-gradient(90deg, #10b981, #34d399);
}

.memory-bar {
  background: linear-gradient(90deg, #a855f7, #c084fc);
}

.disk-bar {
  background: linear-gradient(90deg, #f97316, #fb923c);
}

.info-section {
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  padding: 24px;
  box-shadow: var(--shadow-card);
}

.info-section h2 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 20px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
}

.info-value {
  font-size: 0.9375rem;
  color: var(--text-primary);
  font-family: 'Fira Code', monospace;
}

@media (max-width: 768px) {
  .status-cards {
    grid-template-columns: 1fr;
  }

  .status-card-wide {
    grid-column: span 1;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}

.config-section {
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  padding: 24px;
  box-shadow: var(--shadow-card);
  margin-top: 24px;
}

.config-section h2 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 20px;
}

.loading-inline {
  text-align: center;
  padding: 20px;
  color: var(--text-secondary);
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.config-row {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.config-field {
  flex: 1;
  min-width: 200px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-field label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.config-input {
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  background: var(--bg-surface);
  color: var(--text-primary);
  transition: border-color var(--transition-fast);
}

.config-input:focus {
  outline: none;
  border-color: var(--primary);
}

.config-actions {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.btn-primary {
  padding: 10px 24px;
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: none;
  background: var(--primary);
  color: white;
}

.btn-primary:hover {
  opacity: 0.9;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.config-success {
  color: var(--success, #10b981);
  font-size: 0.875rem;
}

.config-error {
  color: var(--error);
  font-size: 0.875rem;
}
</style>
