<template>
  <div class="tasks-page">
    <div class="page-header">
      <div class="header-content">
        <h1>{{ t('admin.tasks') }}</h1>
        <p class="description">{{ t('admin.tasksDesc') }}</p>
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
        <button class="btn-secondary" @click="reloadAll" :disabled="loading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M23 4v6h-6M1 20v-6h6"/>
            <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
          </svg>
          {{ t('common.refresh') }}
        </button>
      </div>
    </div>

    <div class="filters">
      <div class="filter-group">
        <label>{{ t('admin.userId') }}</label>
        <input
          type="text"
          v-model="filters.userId"
          :placeholder="t('admin.userIdPlaceholder')"
          @keyup.enter="currentPage = 1; loadTasks()"
        />
      </div>
      <div class="filter-group">
        <label>{{ t('admin.status') }}</label>
        <select v-model="filters.status" @change="loadTasks">
          <option value="">{{ t('admin.allStatuses') }}</option>
          <option value="pending">{{ t('admin.pending') }}</option>
          <option value="running">{{ t('admin.running') }}</option>
          <option value="completed">{{ t('admin.completed') }}</option>
          <option value="failed">{{ t('admin.failed') }}</option>
          <option value="cancelled">{{ t('admin.cancelled') }}</option>
        </select>
      </div>
    </div>

    <div v-if="loading && tasks.length === 0" class="loading-state">
      <div class="spinner"></div>
      <p>{{ t('common.loading') }}</p>
    </div>

    <div v-else-if="error && !tasks.length" class="error-state">
      <p>{{ error }}</p>
      <button class="btn-secondary" @click="reloadAll">{{ t('common.retry') }}</button>
    </div>

    <div v-if="error && tasks.length" class="error-banner">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
        <circle cx="12" cy="12" r="10"/>
        <line x1="15" y1="9" x2="9" y2="15"/>
        <line x1="9" y1="9" x2="15" y2="15"/>
      </svg>
      <span>{{ error }}</span>
      <button class="banner-dismiss" @click="error = ''">&times;</button>
    </div>

    <div v-if="tasks.length === 0 && !loading && !error" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M9 11l3 3L22 4"/>
        <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
      </svg>
      <p>{{ t('admin.noTasks') }}</p>
    </div>

    <div v-else-if="tasks.length > 0" class="tasks-table-container">
      <table class="tasks-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>{{ t('admin.userId') }}</th>
            <th>{{ t('admin.status') }}</th>
            <th>{{ t('admin.progress') }}</th>
            <th>{{ t('admin.bestFitness') }}</th>
            <th>{{ t('admin.createdAt') }}</th>
            <th>{{ t('admin.startedAt') }}</th>
            <th>{{ t('admin.completedAt') }}</th>
            <th>{{ t('admin.errorMessage') }}</th>
            <th>{{ t('admin.actions') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="task in paginatedTasks" :key="task.id">
            <td class="cell-id">{{ task.id.substring(0, 8) }}...</td>
            <td class="cell-user" :title="task.userId">{{ resolveUserName(task.userId) }}</td>
            <td>
              <span :class="['badge', `badge-${task.status}`]">{{ task.status }}</span>
            </td>
            <td class="cell-progress">
              <div class="progress-bar">
                <div
                  class="progress-fill"
                  :style="{ width: `${task.totalSteps ? (task.currentStep / task.totalSteps) * 100 : 0}%` }"
                ></div>
              </div>
              <span class="progress-text">{{ task.currentStep }} / {{ task.totalSteps }}</span>
            </td>
              <td class="cell-fitness">
              {{ task.bestFitness != null ? task.bestFitness.toFixed(4) : '-' }}
            </td>
            <td class="cell-date">{{ formatDate(task.createdAt) }}</td>
            <td class="cell-date">{{ formatDate(task.startedAt) }}</td>
            <td class="cell-date">{{ formatDate(task.completedAt) }}</td>
            <td class="cell-error" :title="task.errorMessage">
              {{ task.errorMessage ? (task.errorMessage.length > 30 ? task.errorMessage.substring(0, 30) + '...' : task.errorMessage) : '-' }}
            </td>
            <td class="cell-actions">
              <button class="btn-action btn-logs" @click="viewLogs(task)">
                {{ t('admin.viewLogs') }}
              </button>
              <button
                v-if="task.status === 'running'"
                class="btn-action btn-cancel"
                @click="cancelTask(task)"
                :disabled="actionLoading === task.id"
              >
                {{ t('admin.cancel') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="pagination" v-if="filteredTasks.length > 0">
        <div class="pagination-info">
          {{ t('admin.showing', { start: paginationStart, end: paginationEnd, total: filteredTasks.length }) }}
        </div>
        <div class="pagination-controls">
          <select class="page-size-select" v-model="pageSize" @change="currentPage = 1">
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
          </select>
          <button class="btn-page" :disabled="currentPage <= 1" @click="currentPage--">
            {{ t('admin.previousPage') }}
          </button>
          <template v-for="p in visiblePages" :key="p">
            <span v-if="p === '...'" class="page-ellipsis">...</span>
            <button
              v-else
              class="btn-page"
              :class="{ active: currentPage === p }"
              @click="currentPage = p"
            >
              {{ p }}
            </button>
          </template>
          <button class="btn-page" :disabled="currentPage >= totalPages" @click="currentPage++">
            {{ t('admin.nextPage') }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showLogsDialog" class="dialog-overlay" @click.self="closeLogsDialog">
      <div class="dialog dialog-wide">
        <div class="dialog-header">
          <h3>{{ t('admin.taskLogs') }}: {{ selectedTask?.id?.substring(0, 8) }}...</h3>
          <div class="log-mode-toggle">
            <button class="mode-btn" :class="{ active: selectedLogMode === 'summary' }" @click="changeLogMode('summary')">
              {{ t('console.summary') }}
            </button>
            <button class="mode-btn" :class="{ active: selectedLogMode === 'full' }" @click="changeLogMode('full')">
              {{ t('console.detailed') }}
            </button>
          </div>
          <button class="btn-close" @click="closeLogsDialog">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div class="dialog-body">
          <div v-if="logsLoading" class="loading-state">
            <div class="spinner"></div>
            <p>{{ t('common.loading') }}</p>
          </div>
          <div v-else-if="logsError" class="error-state">
            <p>{{ logsError }}</p>
          </div>
          <template v-else>
            <div v-if="taskDetail" class="detail-summary">
              <div class="detail-row">
                <span class="detail-label">{{ t('admin.status') }}</span>
                <span :class="['badge', `badge-${taskDetail.status}`]">{{ taskDetail.status }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">{{ t('admin.progress') }}</span>
                <span>{{ taskDetail.currentStep }} / {{ taskDetail.totalSteps }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">{{ t('admin.bestFitness') }}</span>
                <span>{{ taskDetail.bestFitness != null ? taskDetail.bestFitness.toFixed(4) : '-' }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">{{ t('admin.createdAt') }}</span>
                <span>{{ formatDate(taskDetail.createdAt) }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">{{ t('admin.startedAt') }}</span>
                <span>{{ formatDate(taskDetail.startedAt) }}</span>
              </div>
              <div class="detail-row">
                <span class="detail-label">{{ t('admin.completedAt') }}</span>
                <span>{{ formatDate(taskDetail.completedAt) }}</span>
              </div>
              <div v-if="taskDetail.errorMessage" class="detail-row">
                <span class="detail-label">{{ t('admin.errorMessage') }}</span>
                <span class="detail-error">{{ taskDetail.errorMessage }}</span>
              </div>
            </div>
            <div v-if="taskLogs.length === 0" class="empty-state">
              <p>{{ t('admin.noLogs') }}</p>
            </div>
            <pre v-else class="logs-content">{{ taskLogs.join('\n') }}</pre>
          </template>
        </div>
        <div class="dialog-footer">
          <button class="btn-secondary" @click="closeLogsDialog">{{ t('common.close') }}</button>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :visible="confirmState.visible"
      :title="confirmState.title"
      :message="confirmState.message"
      :confirmText="confirmState.confirmText"
      :cancelText="confirmState.cancelText"
      :type="confirmState.type"
      @confirm="handleConfirmConfirm"
      @cancel="handleConfirmCancel"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import adminService from '@/services/admin'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const { t } = useI18n()

const confirmState = ref({
  visible: false,
  title: '',
  message: '',
  confirmText: '',
  cancelText: '',
  type: 'info',
  onConfirm: null,
})

const showConfirm = (opts) => {
  return new Promise((resolve) => {
    confirmState.value = {
      visible: true,
      title: opts.title || '',
      message: opts.message || '',
      confirmText: opts.confirmText || t('common.confirm'),
      cancelText: opts.cancelText || t('admin.cancel_action'),
      type: opts.type || 'danger',
      onConfirm: () => { resolve(true) },
      onCancel: () => { resolve(false) },
    }
  })
}

const handleConfirmConfirm = () => {
  confirmState.value.visible = false
  confirmState.value.onConfirm?.()
}

const handleConfirmCancel = () => {
  confirmState.value.visible = false
  confirmState.value.onCancel?.()
}

const tasks = ref([])
const loading = ref(false)
const refreshing = ref(false)
const error = ref('')
const actionLoading = ref(null)
const showLogsDialog = ref(false)
const selectedTask = ref(null)
const taskLogs = ref([])
const taskDetail = ref(null)
const logsLoading = ref(false)
const logsError = ref('')
const userMap = ref({})
const selectedLogMode = ref('summary')

const autoRefresh = ref(false)
const refreshInterval = ref(null)
const REFRESH_INTERVAL_MS = 15000

const currentPage = ref(1)
const pageSize = ref(20)

const filters = reactive({
  userId: '',
  status: ''
})

const filteredTasks = computed(() => {
  return tasks.value
})

const totalPages = computed(() => {
  return Math.max(1, Math.ceil(filteredTasks.value.length / pageSize.value))
})

const paginationStart = computed(() => {
  if (filteredTasks.value.length === 0) return 0
  return (currentPage.value - 1) * pageSize.value + 1
})

const paginationEnd = computed(() => {
  const end = currentPage.value * pageSize.value
  return Math.min(end, filteredTasks.value.length)
})

const paginatedTasks = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredTasks.value.slice(start, start + pageSize.value)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const current = currentPage.value
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1)
  }
  const pages = []
  if (current <= 4) {
    for (let i = 1; i <= 5; i++) pages.push(i)
    pages.push('...')
    pages.push(total)
  } else if (current >= total - 3) {
    pages.push(1)
    pages.push('...')
    for (let i = total - 4; i <= total; i++) pages.push(i)
  } else {
    pages.push(1)
    pages.push('...')
    for (let i = current - 1; i <= current + 1; i++) pages.push(i)
    pages.push('...')
    pages.push(total)
  }
  return pages
})

watch([() => filters.status], () => {
  currentPage.value = 1
})

const resolveUserName = (userId) => {
  if (!userId) return t('admin.unknownUser')
  return userMap.value[userId] || userId
}

const loadUserMap = async () => {
  try {
    const users = await adminService.getAdminUsers()
    const map = {}
    users.forEach(u => { map[u.id] = u.displayName || u.username })
    userMap.value = map
  } catch {
    userMap.value = {}
  }
}

const loadTasks = async () => {
  loading.value = true
  error.value = ''
  try {
    const params = {}
    if (filters.userId) params.user_id = filters.userId
    if (filters.status) params.status = filters.status
    tasks.value = await adminService.getAdminTasks(params)
  } catch (e) {
    error.value = e.message || t('admin.loadTasksError')
  } finally {
    loading.value = false
  }
}

const reloadAll = async () => {
  await Promise.all([loadTasks(), loadUserMap()])
}

const viewLogs = async (task, mode = 'summary') => {
  selectedTask.value = task
  selectedLogMode.value = mode
  showLogsDialog.value = true
  logsLoading.value = true
  logsError.value = ''
  taskLogs.value = []
  taskDetail.value = null
  try {
    const [logs, detail] = await Promise.all([
      adminService.getAdminTaskLogs(task.id, mode),
      adminService.getAdminTaskDetail(task.id).catch(() => null)
    ])
    taskLogs.value = logs
    taskDetail.value = detail
  } catch (e) {
    logsError.value = e.message || t('admin.loadLogsError')
  } finally {
    logsLoading.value = false
  }
}

const closeLogsDialog = () => {
  showLogsDialog.value = false
  selectedTask.value = null
  selectedLogMode.value = 'summary'
  taskLogs.value = []
  taskDetail.value = null
  logsError.value = ''
}

const refreshLogsIfOpen = async (mode = 'summary') => {
  if (!showLogsDialog.value || !selectedTask.value) return
  logsLoading.value = true
  logsError.value = ''
  try {
    const [logs, detail] = await Promise.all([
      adminService.getAdminTaskLogs(selectedTask.value.id, mode),
      adminService.getAdminTaskDetail(selectedTask.value.id).catch(() => null)
    ])
    taskLogs.value = logs
    taskDetail.value = detail
  } catch (e) {
    logsError.value = e.message || t('admin.loadLogsError')
  } finally {
    logsLoading.value = false
  }
}

const changeLogMode = async (mode) => {
  selectedLogMode.value = mode
  if (selectedTask.value) {
    await refreshLogsIfOpen(mode)
  }
}

const cancelTask = async (task) => {
  const confirmed = await showConfirm({
    title: t('admin.cancel'),
    message: t('admin.confirmCancel'),
    type: 'danger',
  })
  if (!confirmed) return
  actionLoading.value = task.id
  try {
    await adminService.cancelAdminTask(task.id)
    await loadTasks()
  } catch (e) {
    error.value = e.message || t('admin.cancelTaskError')
  } finally {
    actionLoading.value = null
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
    refreshInterval.value = setInterval(async () => {
      if (refreshing.value) return
      refreshing.value = true
      try {
          await refreshLogsIfOpen(selectedLogMode.value)
          await Promise.all([loadTasks(), loadUserMap()])
        } finally {
          refreshing.value = false
      }
    }, REFRESH_INTERVAL_MS)
  }
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  loadUserMap()
  loadTasks()
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
    refreshInterval.value = null
  }
})
</script>

<style scoped>
.tasks-page {
  max-width: 1400px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
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

.log-mode-toggle {
  display: flex;
  gap: 6px;
  margin-left: auto;
  margin-right: 12px;
}

.mode-btn {
  padding: 6px 12px;
  border: 1px solid var(--border);
  background: var(--bg-surface);
  color: var(--text-secondary);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.8125rem;
  transition: all var(--transition-fast);
}

.mode-btn:hover {
  background: var(--bg-surface-alt);
  color: var(--text-primary);
}

.mode-btn.active {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.filters {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
  padding: 16px 20px;
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-group label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
}

.filter-group input, .filter-group select {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  background: var(--bg-primary);
  color: var(--text-primary);
  min-width: 160px;
}

.filter-group input:focus, .filter-group select:focus {
  outline: none;
  border-color: var(--primary);
}

.btn-primary, .btn-secondary {
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
}

.btn-secondary {
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

.loading-state, .empty-state, .error-state {
  text-align: center;
  padding: 48px;
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
}

.spinner {
  width: 36px;
  height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state svg {
  width: 56px;
  height: 56px;
  color: var(--text-muted);
  margin-bottom: 12px;
}

.error-state {
  color: var(--error);
}

.error-state p {
  margin-bottom: 12px;
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

.tasks-table-container {

  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  overflow: hidden;
  box-shadow: var(--shadow-card);
}

.tasks-table {
  width: 100%;
  border-collapse: collapse;
}

.tasks-table th {
  text-align: left;
  padding: 14px 16px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
  background: var(--bg-surface-alt);
  border-bottom: 1px solid var(--border);
}

.tasks-table td {
  padding: 14px 16px;
  font-size: 0.875rem;
  color: var(--text-primary);
  border-bottom: 1px solid var(--border);
}

.tasks-table tr:last-child td {
  border-bottom: none;
}

.tasks-table tr:hover td {
  background: var(--bg-surface-alt);
}

.cell-id {
  font-family: 'Fira Code', monospace;
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.cell-user {
  font-family: 'Fira Code', monospace;
}

.cell-progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-bar {
  width: 80px;
  height: 6px;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--primary);
  border-radius: var(--radius-full);
  transition: width 0.3s ease;
}

.progress-text {
  font-size: 0.75rem;
  color: var(--text-muted);
  white-space: nowrap;
}

.cell-fitness {
  font-family: 'Fira Code', monospace;
  font-size: 0.8125rem;
}

.cell-date {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.cell-error {
  font-size: 0.8125rem;
  color: #ef4444;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: capitalize;
}

.badge-pending {
  background: rgba(234, 179, 8, 0.15);
  color: #eab308;
}

.badge-running {
  background: rgba(59, 130, 246, 0.15);
  color: #3b82f6;
}

.badge-completed {
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
}

.badge-failed {
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
}

.badge-cancelled {
  background: rgba(107, 114, 128, 0.15);
  color: #6b7280;
}

.cell-actions {
  display: flex;
  gap: 8px;
  white-space: nowrap;
}

.btn-action {
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid transparent;
}

.btn-logs {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border-color: rgba(59, 130, 246, 0.2);
}

.btn-logs:hover {
  background: rgba(59, 130, 246, 0.2);
}

.btn-cancel {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.2);
}

.btn-cancel:hover {
  background: rgba(239, 68, 68, 0.2);
}

.btn-action:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-top: 1px solid var(--border);
  background: var(--bg-surface-alt);
}

.pagination-info {
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 6px;
}

.page-size-select {
  padding: 6px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  background: var(--bg-primary);
  color: var(--text-primary);
  margin-right: 8px;
}

.page-size-select:focus {
  outline: none;
  border-color: var(--primary);
}

.btn-page {
  min-width: 32px;
  height: 32px;
  padding: 0 8px;
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid var(--border);
  background: var(--bg-surface);
  color: var(--text-secondary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.btn-page:hover:not(:disabled) {
  background: var(--bg-surface-alt);
  color: var(--text-primary);
}

.btn-page.active {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
}

.btn-page:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-ellipsis {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  height: 32px;
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.dialog {
  background: var(--bg-surface);
  border-radius: var(--radius-xl);
  width: 100%;
  max-width: 480px;
  box-shadow: var(--shadow-lg);
}

.dialog-wide {
  max-width: 800px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  flex-shrink: 0;
}

.dialog-header h3 {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary);
}

.btn-close {
  background: none;
  border: none;
  padding: 4px;
  cursor: pointer;
  color: var(--text-muted);
  border-radius: var(--radius-sm);
}

.btn-close:hover {
  background: var(--bg-surface-alt);
  color: var(--text-primary);
}

.btn-close svg {
  width: 20px;
  height: 20px;
}

.dialog-body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.logs-content {
  background: var(--bg-primary);
  padding: 16px;
  border-radius: var(--radius-md);
  font-family: 'Fira Code', monospace;
  font-size: 0.8125rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 400px;
  overflow-y: auto;
  color: var(--text-secondary);
}

.detail-summary {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px 24px;
  padding: 16px;
  margin-bottom: 16px;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-md);
}

.detail-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--text-muted);
}

.detail-error {
  color: #ef4444;
  font-size: 0.8125rem;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 12px 20px;
  border-top: 1px solid var(--border);
  background: var(--bg-surface-alt);
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
  flex-shrink: 0;
}
</style>
