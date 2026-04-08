<template>
  <div class="server-status" :class="statusClass">
    <div class="status-header">
      <div class="status-indicator">
        <span class="status-dot"></span>
        <span class="status-label">{{ statusLabel }}</span>
      </div>
      <span class="status-time">{{ currentTime }}</span>
    </div>
    
    <div class="status-body">
      <div class="status-info-grid">
        <div class="info-item">
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
          <div class="info-content">
            <span class="info-label">CPU</span>
            <span class="info-value">{{ cpuPercent }}%</span>
          </div>
          <div class="cpu-bar">
            <div class="cpu-fill" :style="{ width: cpuPercent + '%' }"></div>
          </div>
        </div>

        <div class="info-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 00-3-3.87"/>
            <path d="M16 3.13a4 4 0 010 7.75"/>
          </svg>
          <div class="info-content">
            <span class="info-label">{{ t('serverStatus.currentJobs') }}</span>
            <span class="info-value">{{ activeJobs }}</span>
          </div>
        </div>

        <div class="info-item">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
          </svg>
          <div class="info-content">
            <span class="info-label">{{ t('serverStatus.maxJobs') }}</span>
            <span class="info-value">{{ effectiveMaxJobs }}</span>
          </div>
        </div>
      </div>

      <div class="status-message">
        <p>{{ statusMessage }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/index'

const { t } = useI18n()

const props = defineProps({
  maxJobs: {
    type: Number,
    default: 1
  },
  pollingInterval: {
    type: Number,
    default: 5000
  }
})

const emit = defineEmits(['status-change'])

const cpuPercent = ref(0)
const activeJobs = ref(0)
const backendMaxJobs = ref(props.maxJobs)
const backendMaxOmpThreads = ref(1)
const currentTime = ref('')
let pollingTimer = null

const effectiveMaxJobs = computed(() => {
  return backendMaxJobs.value || props.maxJobs
})

const statusClass = computed(() => {
  if (cpuPercent.value > 85 || activeJobs.value >= effectiveMaxJobs.value) return 'full'
  if (cpuPercent.value > 50 || activeJobs.value > 0) return 'busy'
  return 'idle'
})

const statusLabel = computed(() => {
  if (statusClass.value === 'full') return t('serverStatus.statusFull')
  if (statusClass.value === 'busy') return t('serverStatus.statusBusy')
  return t('serverStatus.statusIdle')
})

const statusMessage = computed(() => {
  if (statusClass.value === 'full') return t('serverStatus.msgFull')
  if (statusClass.value === 'busy') return t('serverStatus.msgBusy')
  return t('serverStatus.msgIdle')
})

const isServerAvailable = computed(() => {
  return statusClass.value !== 'full'
})

const updateTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString()
}

const fetchStatus = async () => {
  try {
    const result = await api.getServerStatus()
    if (result.success) {
      cpuPercent.value = result.data.cpuPercent || 0
      activeJobs.value = result.data.activeJobs || 0
      if (result.data.maxJobs !== undefined) {
        backendMaxJobs.value = result.data.maxJobs
      }
      if (result.data.maxOmpThreads !== undefined) {
        backendMaxOmpThreads.value = result.data.maxOmpThreads
      }
    }
  } catch (error) {
    cpuPercent.value = Math.floor(Math.random() * 30)
    activeJobs.value = 0
  }
  emit('status-change', {
    available: isServerAvailable.value,
    cpuPercent: cpuPercent.value,
    activeJobs: activeJobs.value
  })
}

const startPolling = () => {
  updateTime()
  fetchStatus()
  pollingTimer = setInterval(() => {
    updateTime()
    fetchStatus()
  }, props.pollingInterval)
}

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

defineExpose({
  isServerAvailable,
  cpuPercent,
  activeJobs
})

onMounted(() => {
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.server-status {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: all var(--transition-normal);
}

.server-status.idle {
  border-color: var(--secondary);
}

.server-status.busy {
  border-color: var(--cta);
}

.server-status.full {
  border-color: var(--error);
}

.status-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-surface-alt);
  border-bottom: 1px solid var(--border);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--text-muted);
}

.idle .status-dot {
  background: var(--secondary);
  box-shadow: 0 0 8px var(--secondary);
}

.busy .status-dot {
  background: var(--cta);
  animation: pulse 2s infinite;
}

.full .status-dot {
  background: var(--error);
  animation: pulse 1s infinite;
}

.status-label {
  font-weight: 600;
  font-size: 0.875rem;
}

.idle .status-label {
  color: var(--secondary);
}

.busy .status-label {
  color: var(--cta);
}

.full .status-label {
  color: var(--error);
}

.status-time {
  font-size: 0.75rem;
  font-family: 'Fira Code', monospace;
  color: var(--text-muted);
}

.status-body {
  padding: 16px;
}

.status-info-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-md);
  text-align: center;
}

.info-item svg {
  width: 24px;
  height: 24px;
  color: var(--primary);
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-label {
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
}

.info-value {
  font-size: 1.25rem;
  font-weight: 700;
  font-family: 'Fira Code', monospace;
  color: var(--text-primary);
}

.cpu-bar {
  width: 100%;
  height: 4px;
  background: var(--border);
  border-radius: 2px;
  overflow: hidden;
}

.cpu-fill {
  height: 100%;
  background: var(--primary);
  border-radius: 2px;
  transition: width 0.5s ease;
}

.idle .cpu-fill {
  background: var(--secondary);
}

.busy .cpu-fill {
  background: var(--cta);
}

.full .cpu-fill {
  background: var(--error);
}

.status-message {
  padding: 12px;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-md);
  text-align: center;
}

.status-message p {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  margin: 0;
}

.full .status-message {
  background: rgba(239, 68, 68, 0.1);
}

.full .status-message p {
  color: var(--error);
  font-weight: 500;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
