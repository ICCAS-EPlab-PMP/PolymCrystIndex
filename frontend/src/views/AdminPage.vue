<template>
  <div class="admin-overview">
    <div class="page-header">
      <div class="header-left">
        <h1>{{ t('modules.admin.title') }}</h1>
        <p class="subtitle">{{ t('modules.admin.desc') }}</p>
      </div>
      <button v-if="dashboardData" class="btn-refresh" @click="loadDashboard" :disabled="loading">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M23 4v6h-6M1 20v-6h6"/>
          <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
        </svg>
      </button>
    </div>

    <div v-if="dashboardData" class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon stat-users">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ dashboardData.totalUsers }}</span>
          <span class="stat-label">{{ t('admin.totalUsers') }}</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon stat-active">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
            <circle cx="8.5" cy="7" r="4"/>
            <line x1="20" y1="8" x2="20" y2="14"/>
            <line x1="23" y1="11" x2="17" y2="11"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ dashboardData.activeUsers }}</span>
          <span class="stat-label">{{ t('admin.activeUsers') }}</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon stat-running">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ dashboardData.runningTasks }}</span>
          <span class="stat-label">{{ t('admin.runningTasks') }}</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon stat-completed">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ dashboardData.completedTasks }}</span>
          <span class="stat-label">{{ t('admin.completedTasks') }}</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon stat-failed">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ dashboardData.failedTasks }}</span>
          <span class="stat-label">{{ t('admin.failedTasks') }}</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon stat-total-tasks">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
            <polyline points="10 9 9 9 8 9"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-value">{{ dashboardData.totalTasks }}</span>
          <span class="stat-label">{{ t('admin.totalTasks') }}</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-icon stat-cpu">
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
        <div class="stat-content">
          <span class="stat-value">{{ dashboardData.cpuPercent?.toFixed(1) || 0 }}%</span>
          <span class="stat-label">{{ t('admin.cpuPercent') }}</span>
        </div>
      </div>

      <div class="stat-card stat-wide">
        <div class="stat-icon" :class="statusIconClass">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path v-if="dashboardData.systemStatus === 'idle'" d="M8 12l2 2 4-4"/>
            <path v-else-if="dashboardData.systemStatus === 'busy'" d="M12 8v4l3 3"/>
            <path v-else d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3M12 17h.01"/>
          </svg>
        </div>
        <div class="stat-content">
          <span class="stat-value" :class="statusTextClass">{{ statusLabel }}</span>
          <span class="stat-label">{{ t('admin.uptime') }}: {{ dashboardData.uptime }}</span>
        </div>
      </div>
    </div>

    <div v-else-if="loading" class="stats-loading">
      <div class="spinner"></div>
    </div>

    <div v-else-if="dashboardError" class="stats-error">
      <p>{{ dashboardError }}</p>
    </div>

    <div class="nav-section">
      <h2 class="nav-section-title">{{ t('admin.overview') }}</h2>
      <div class="cards-grid">
        <router-link to="/admin/users" class="nav-card">
          <div class="card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
              <circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 00-3-3.87"/>
              <path d="M16 3.13a4 4 0 010 7.75"/>
            </svg>
          </div>
          <div class="card-content">
            <h3>{{ t('admin.users') }}</h3>
            <p>{{ t('admin.usersDesc') }}</p>
          </div>
          <div class="card-arrow">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </div>
        </router-link>

        <router-link to="/admin/tasks" class="nav-card">
          <div class="card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M9 11l3 3L22 4"/>
              <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
            </svg>
          </div>
          <div class="card-content">
            <h3>{{ t('admin.tasks') }}</h3>
            <p>{{ t('admin.tasksDesc') }}</p>
          </div>
          <div class="card-arrow">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </div>
        </router-link>

        <router-link to="/admin/system" class="nav-card">
          <div class="card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
              <line x1="8" y1="21" x2="16" y2="21"/>
              <line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
          </div>
          <div class="card-content">
            <h3>{{ t('admin.system') }}</h3>
            <p>{{ t('admin.systemDesc') }}</p>
          </div>
          <div class="card-arrow">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
          </div>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import adminService from '@/services/admin'

const { t } = useI18n()

const dashboardData = ref(null)
const loading = ref(false)
const dashboardError = ref('')

const statusLabel = computed(() => {
  const s = dashboardData.value?.systemStatus
  if (s === 'idle') return t('admin.systemHealthy')
  if (s === 'busy') return t('admin.systemBusy')
  if (s === 'full') return t('admin.systemFull')
  return '-'
})

const statusIconClass = computed(() => {
  const s = dashboardData.value?.systemStatus
  if (s === 'idle') return 'stat-idle'
  if (s === 'busy') return 'stat-busy'
  if (s === 'full') return 'stat-full'
  return ''
})

const statusTextClass = computed(() => {
  const s = dashboardData.value?.systemStatus
  if (s === 'idle') return 'text-idle'
  if (s === 'busy') return 'text-busy'
  if (s === 'full') return 'text-full'
  return ''
})

const loadDashboard = async () => {
  loading.value = true
  dashboardError.value = ''
  try {
    dashboardData.value = await adminService.getDashboard()
  } catch (e) {
    dashboardError.value = e.message || t('admin.loadDashboardError')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadDashboard()
})
</script>

<style scoped>
.admin-overview {
  max-width: 1000px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
}

.header-left h1 {
  font-size: 2rem;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.subtitle {
  font-size: 1.0625rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

.btn-refresh {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 10px;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all var(--transition-fast);
}

.btn-refresh:hover {
  background: var(--bg-surface-alt);
  color: var(--text-primary);
}

.btn-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-refresh svg {
  width: 20px;
  height: 20px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 40px;
}

.stat-card {
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  padding: 20px;
  box-shadow: var(--shadow-card);
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-wide {
  grid-column: span 4;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon svg {
  width: 24px;
  height: 24px;
}

.stat-users {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.stat-active {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.stat-running {
  background: rgba(168, 85, 247, 0.15);
  color: #a855f7;
}

.stat-completed {
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
}

.stat-failed {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.stat-total-tasks {
  background: rgba(107, 114, 128, 0.15);
  color: #6b7280;
}

.stat-cpu {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.stat-idle {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.stat-busy {
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
}

.stat-full {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.stat-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-primary);
  font-family: 'Fira Code', monospace;
}

.text-idle {
  color: #10b981;
}

.text-busy {
  color: #eab308;
}

.text-full {
  color: #ef4444;
}

.stat-label {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.stats-loading {
  display: flex;
  justify-content: center;
  padding: 40px;
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  margin-bottom: 40px;
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.stats-error {
  padding: 20px;
  background: rgba(239, 68, 68, 0.1);
  border-radius: var(--radius-lg);
  margin-bottom: 40px;
  color: var(--error);
  font-size: 0.875rem;
}

.nav-section {
  margin-top: 8px;
}

.nav-section-title {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.nav-card {
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  padding: 28px;
  box-shadow: var(--shadow-card);
  display: flex;
  flex-direction: column;
  gap: 20px;
  text-decoration: none;
  transition: all var(--transition-normal);
  border: 1px solid transparent;
}

.nav-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
  border-color: var(--primary);
}

.nav-card:hover .card-icon {
  background: var(--primary-bg);
  color: var(--primary);
}

.nav-card:hover .card-arrow {
  color: var(--primary);
  transform: translateX(4px);
}

.card-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-lg);
  background: var(--bg-surface-alt);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--transition-fast);
}

.card-icon svg {
  width: 28px;
  height: 28px;
  color: var(--text-secondary);
}

.card-content {
  flex: 1;
}

.card-content h3 {
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.card-content p {
  font-size: 0.875rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

.card-arrow {
  color: var(--text-muted);
  transition: all var(--transition-fast);
  align-self: flex-end;
}

.card-arrow svg {
  width: 20px;
  height: 20px;
}

@media (max-width: 1100px) {
  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
  }
  .stat-wide {
    grid-column: span 3;
  }
  .cards-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .stat-wide {
    grid-column: span 2;
  }
}

@media (max-width: 500px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
  .stat-wide {
    grid-column: span 1;
  }
}
</style>
