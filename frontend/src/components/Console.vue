<template>
  <div class="console">
    <div class="page-header">
      <h2>{{ t('console.title') }}</h2>
      <p>{{ t('console.subtitle') }}</p>
    </div>

    <ServerStatus 
      :polling-interval="5000"
      @status-change="handleServerStatus"
      ref="serverStatusRef"
    />

    <div class="status-bar">
      <div class="status-info">
        <span class="status-label">{{ t('console.status') }}:</span>
        <span class="status-value" :class="statusClass">
          <span class="status-dot"></span>
          {{ statusText }}
        </span>
      </div>
      <div class="progress-info" v-if="isRunning">
        <span>{{ t('console.generation', { current: currentGen + 1, total: params.steps }) }}</span>
        <span class="current-error">{{ t('console.currentError', { value: bestFitness.toFixed(6) }) }}</span>
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
        </div>
      </div>
    </div>

    <div class="console-output">
      <div class="console-header">
        <span>{{ t('console.outputLog') }}</span>
        <div class="log-mode-toggle">
          <button
            :class="{ active: logMode === 'summary' }"
            @click="setLogMode('summary')"
            class="mode-btn"
          >
            {{ t('console.summary') }}
          </button>
          <button
            :class="{ active: logMode === 'full' }"
            @click="setLogMode('full')"
            class="mode-btn"
          >
            {{ t('console.detailed') }}
          </button>
        </div>
        <button v-if="logs.length" class="btn-clear" @click="clearLogs">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3,6 5,6 21,6"/>
            <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
          </svg>
          {{ t('console.clear') }}
        </button>
      </div>
      <div class="console-body" ref="consoleBody">
        <div v-if="!logs.length" class="console-empty">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <polyline points="4,17 10,11 4,5"/>
            <line x1="12" y1="19" x2="20" y2="19"/>
          </svg>
          <span>{{ t('console.waiting') }}</span>
        </div>
        <div v-for="(log, index) in logs" :key="index" class="log-line" :class="getLogClass(log)">
          {{ log }}
        </div>
      </div>
    </div>

    <div class="console-actions">
      <div class="action-info">
        <div v-if="!dataFile || !dataFile.file" class="info-warning">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <span>{{ t('console.uploadFirst') }}</span>
        </div>
        <div v-else class="info-ready">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
            <polyline points="22,4 12,14.01 9,11.01"/>
          </svg>
          <span>{{ t('console.dataReady', { filename: dataFile.file.name }) }}</span>
        </div>
      </div>

      <div class="action-buttons">
        <button
          v-if="isRunning"
          class="btn-export-step"
          @click="exportCurrentStep"
          :title="t('console.exportStepHint')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="7,10 12,15 17,10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          {{ t('console.exportStep') }}
        </button>

        <button
          v-if="isRunning"
          class="btn-cancel"
          @click="cancelAnalysis"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
          {{ t('console.cancel') }}
        </button>

        <button
          class="btn-run"
          :class="{ running: isRunning }"
          :disabled="!dataFile || isRunning || !serverAvailable"
          @click="startAnalysis"
        >
          <span v-if="isRunning" class="spinner"></span>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="5,3 19,12 5,21 5,3"/>
          </svg>
          <span>{{ isRunning ? t('console.running') : t('console.startAnalysis') }}</span>
        </button>
      </div>
    </div>

    <div v-if="analysisComplete" class="success-message">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
        <polyline points="22,4 12,14.01 9,11.01"/>
      </svg>
      <div class="success-content">
        <span class="success-title">{{ t('console.analysisComplete') }}</span>
        <span class="success-desc">{{ t('console.bestFitness', { value: bestFitness }) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onUnmounted, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/index'
import ServerStatus from './ServerStatus.vue'

const { t } = useI18n()
const props = defineProps({
  params: {
    type: Object,
    required: true
  },
  dataFile: {
    type: [File, null],
    default: null
  },
  taskId: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['navigate', 'task-started', 'run-status-change'])

const isRunning = ref(false)
const analysisComplete = ref(false)
const localRunStatus = ref('idle')
const currentGen = ref(0)
const bestFitness = ref(0)
const logs = ref([])
const consoleBody = ref(null)
const serverAvailable = ref(true)
const serverStatusRef = ref(null)
const currentTaskId = ref(null)
const statusPollingTimer = ref(null)
const logsPollingTimer = ref(null)
const logMode = ref('summary')

const buildPeakSymmetrySummaryLines = (resultData) => {
  const groups = Array.isArray(resultData?.peakSymmetryGroups) ? resultData.peakSymmetryGroups : []
  const twoPeakCount = groups.filter(group => group?.groupType === '2-peak').length
  const fourPeakCount = groups.filter(group => group?.groupType === '4-peak').length
  const enabled = Boolean(resultData?.peakSymmetryConfig?.enabled)

  if (!enabled) {
    return ['[System] Peak symmetry merge mode: disabled']
  }

  return [
    `[System] Peak symmetry merge mode: enabled (Tq=${resultData?.peakSymmetryConfig?.mergeTq ?? 0.02}, Ta=${resultData?.peakSymmetryConfig?.mergeTa ?? 1.0})`,
    `[System] Peak symmetry groups summary: 2-peak=${twoPeakCount}, 4-peak=${fourPeakCount}, total=${groups.length}`
  ]
}

const buildGlideSummaryLines = (resultData) => {
  const glide = resultData?.glideBatchOutputs || { enabled: false, groups: [] }
  const groups = Array.isArray(glide.groups) ? glide.groups : []
  if (!glide.enabled) {
    return ['[System] Glide-shear batches: disabled']
  }

  return [
    `[System] Glide-shear batches: enabled (${groups.length} group${groups.length === 1 ? '' : 's'})`,
    `[System] Glide batch root: ${glide.batchRoot || '—'}`,
  ]
}

const appendResultSummaryLogs = async () => {
  try {
    const result = await api.getResults()
    if (!result.success || !result.data) {
      return
    }

    const summaryLines = [
      ...buildPeakSymmetrySummaryLines(result.data),
      ...buildGlideSummaryLines(result.data),
    ]
    for (const line of summaryLines) {
      if (!logs.value.includes(line)) {
        logs.value.push(line)
      }
    }
    await scrollToBottom()
  } catch (error) {
    console.error('Result summary load error:', error)
  }
}

const handleServerStatus = (status) => {
  serverAvailable.value = status.available
}

const statusClass = computed(() => {
  if (localRunStatus.value === 'running') return 'running'
  if (localRunStatus.value === 'completed') return 'success'
  if (localRunStatus.value === 'failed' || localRunStatus.value === 'error') return 'error'
  if (localRunStatus.value === 'cancelled') return 'cancelled'
  return 'idle'
})

const statusText = computed(() => {
  if (localRunStatus.value === 'running') return t('status.running')
  if (localRunStatus.value === 'completed') return t('status.completed')
  if (localRunStatus.value === 'failed') return t('status.failed')
  if (localRunStatus.value === 'error') return t('status.error')
  if (localRunStatus.value === 'cancelled') return t('status.cancelled')
  return t('status.idle')
})

const progressPercent = computed(() => {
  if (!props.params.steps) return 0
  return Math.round(((currentGen.value + 1) / props.params.steps) * 100)
})

const updateRunStatus = (status) => {
  localRunStatus.value = status
  emit('run-status-change', status)
}

const startAnalysis = async () => {
  if (!props.dataFile) {
    logs.value.push('[Error] No data file uploaded')
    updateRunStatus('error')
    return
  }

  isRunning.value = true
  analysisComplete.value = false
  updateRunStatus('running')
  currentGen.value = 0
  bestFitness.value = 0
  logs.value = []
  currentTaskId.value = null

  const fileToUpload = props.dataFile.file || props.dataFile

  try {
    logs.value.push('[System] Uploading diffraction file...')
    await scrollToBottom()
    
    const uploadResult = await api.uploadData(fileToUpload)
    if (!uploadResult.success) {
      throw new Error(uploadResult.message || 'File upload failed')
    }
    
    logs.value.push(`[System] File uploaded: ${uploadResult.data.filename} (${uploadResult.data.pointCount} points)`)
    await scrollToBottom()
    
    logs.value.push('[System] Starting analysis...')
    await scrollToBottom()
    
    const runResult = await api.runAnalysis(uploadResult.data.path, props.params)
    if (!runResult.success) {
      throw new Error(runResult.message || 'Failed to start analysis')
    }
    
    currentTaskId.value = runResult.data.taskId
    emit('task-started', currentTaskId.value)
    logs.value.push(`[System] Task started: ${currentTaskId.value}`)

    startStatusPolling()
    startLogsPolling()

  } catch (error) {
    logs.value.push(`[Error] ${error.message || 'Failed to connect to server'}`)
    isRunning.value = false
    analysisComplete.value = false
    updateRunStatus('error')
  }
}

const scrollToBottom = async () => {
  await nextTick()
  if (consoleBody.value) {
    consoleBody.value.scrollTop = consoleBody.value.scrollHeight
  }
}

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms))

const startStatusPolling = () => {
  statusPollingTimer.value = setInterval(async () => {
    if (!currentTaskId.value || !isRunning.value) {
      stopStatusPolling()
      return
    }

    try {
      const result = await api.getAnalysisStatus(currentTaskId.value)

      if (!result.success) {
        logs.value.push(`[Error] ${result.message || 'Status check failed'}`)
        stopStatusPolling()
        return
      }

      const { status, currentGen: gen, bestFitness: fitness } = result.data

      if (gen !== undefined) currentGen.value = gen
      if (fitness !== undefined) bestFitness.value = fitness

      if (status === 'completed') {
        logs.value.push('[System] Analysis completed successfully')
        isRunning.value = false
        analysisComplete.value = true
        updateRunStatus('completed')
        emit('navigate', 'results')
        await appendResultSummaryLogs()
        stopStatusPolling()
        stopLogsPolling()
      } else if (status === 'failed') {
        logs.value.push(`[Error] Analysis failed: ${result.data.error || 'Unknown error'}`)
        isRunning.value = false
        analysisComplete.value = false
        updateRunStatus('failed')
        stopStatusPolling()
        stopLogsPolling()
      } else if (status === 'cancelled') {
        logs.value.push('[System] Analysis was cancelled')
        isRunning.value = false
        analysisComplete.value = false
        updateRunStatus('cancelled')
        stopStatusPolling()
        stopLogsPolling()
      } else if (status === 'running') {
        if (!isRunning.value) {
          isRunning.value = true
        }
        updateRunStatus('running')
      }

      await scrollToBottom()
    } catch (error) {
      console.error('Status polling error:', error)
    }
  }, 500)
}

const stopStatusPolling = () => {
  if (statusPollingTimer.value) {
    clearInterval(statusPollingTimer.value)
    statusPollingTimer.value = null
  }
}

const startLogsPolling = () => {
  logsPollingTimer.value = setInterval(async () => {
    if (!currentTaskId.value || !isRunning.value) {
      stopLogsPolling()
      return
    }

    try {
      const result = await api.getAnalysisLogs(currentTaskId.value, logMode.value)

      if (result.success && result.data?.logs) {
        const newLogs = result.data.logs
        if (newLogs.length > logs.value.length) {
          logs.value = newLogs
          await scrollToBottom()
        }
      }
    } catch (error) {
      console.error('Logs polling error:', error)
    }
  }, 1000)
}

const stopLogsPolling = () => {
  if (logsPollingTimer.value) {
    clearInterval(logsPollingTimer.value)
    logsPollingTimer.value = null
  }
}

const cancelAnalysis = async () => {
  if (!currentTaskId.value) return

  try {
    const result = await api.cancelAnalysis(currentTaskId.value)
    if (result.success) {
      logs.value.push('[System] Cancellation requested')
      isRunning.value = false
      analysisComplete.value = false
      updateRunStatus('cancelled')
      stopStatusPolling()
      stopLogsPolling()
    } else {
      logs.value.push(`[Error] ${result.message || 'Cancellation failed'}`)
      updateRunStatus('error')
    }
  } catch (error) {
    logs.value.push(`[Error] ${error.message || 'Cancellation request failed'}`)
    updateRunStatus('error')
  }
}

const clearLogs = () => {
  logs.value = []
}

const setLogMode = (mode) => {
  logMode.value = mode
  if (currentTaskId.value && isRunning.value) {
    api.getAnalysisLogs(currentTaskId.value, mode).then(result => {
      if (result.success && result.data?.logs) {
        logs.value = result.data.logs
      }
    })
  }
}

const getLogClass = (log) => {
  if (log.includes('[System]')) return 'log-system'
  if (log.includes('[Progress]')) return 'log-progress'
  if (log.includes('[Best]')) return 'log-best'
  if (log.includes('[Generation')) return 'log-generation'
  if (log.includes('[Error]') || log.includes('[ERROR]')) return 'log-error'
  if (log.includes('[Warning]') || log.includes('[WARNING]')) return 'log-warning'
  return ''
}

const exportCurrentStep = () => {
  const stepData = {
    generation: currentGen.value,
    bestFitness: bestFitness.value,
    timestamp: new Date().toISOString(),
    progress: progressPercent.value
  }
  const content = JSON.stringify(stepData, null, 2)
  const blob = new Blob([content], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `step_${currentGen.value}_fitness_${bestFitness.value}.json`
  a.click()
  URL.revokeObjectURL(url)
}

watch(() => props.dataFile, () => {
  analysisComplete.value = false
  if (!isRunning.value) {
    updateRunStatus('idle')
  }
})

onMounted(async () => {
  if (!props.taskId) {
    updateRunStatus('idle')
    return
  }

  try {
    const statusResult = await api.getAnalysisStatus(props.taskId)
    if (!statusResult.success) {
      logs.value.push('[System] Previous task not found. Starting fresh.')
      updateRunStatus('idle')
      return
    }

    const { status, currentGen: gen, bestFitness: fitness } = statusResult.data
    currentTaskId.value = props.taskId
    currentGen.value = gen || 0
    bestFitness.value = fitness || 0

    if (status === 'running') {
      isRunning.value = true
      logs.value.push(`[System] Restored running task: ${props.taskId}`)
      updateRunStatus('running')
      startStatusPolling()
      startLogsPolling()
    } else if (status === 'completed') {
      isRunning.value = false
      analysisComplete.value = true
      logs.value.push(`[System] Restored completed task: ${props.taskId}`)
      updateRunStatus('completed')
      await appendResultSummaryLogs()
    } else if (status === 'failed') {
      isRunning.value = false
      analysisComplete.value = false
      logs.value.push(`[System] Previous task failed: ${props.taskId}`)
      updateRunStatus('failed')
    } else if (status === 'cancelled') {
      isRunning.value = false
      analysisComplete.value = false
      logs.value.push(`[System] Previous task was cancelled: ${props.taskId}`)
      updateRunStatus('cancelled')
    }
  } catch (error) {
    logs.value.push('[System] Failed to restore previous task. Starting fresh.')
    updateRunStatus('idle')
  }
})

onUnmounted(() => {
  stopStatusPolling()
  stopLogsPolling()
})
</script>

<style scoped>
.console {
  max-width: 1000px;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 1.75rem;
  margin-bottom: 8px;
}

.page-header p {
  color: var(--text-secondary);
}

.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  margin-bottom: 16px;
}

.status-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.status-value {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-family: 'Fira Code', monospace;
}

.status-value.idle {
  color: var(--text-muted);
}

.status-value.running {
  color: var(--status-running);
}

.status-value.success {
  color: var(--status-success);
}

.status-value.error {
  color: var(--status-error);
}

.status-value.cancelled {
  color: var(--text-secondary);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
}

.status-value.running .status-dot {
  animation: pulse 2s infinite;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 0.875rem;
  font-family: 'Fira Code', monospace;
  color: var(--text-secondary);
}

.progress-bar {
  width: 200px;
  height: 6px;
  background: var(--bg-surface-alt);
  border-radius: 3px;
  overflow: hidden;
}

.current-error {
  color: var(--primary);
  font-weight: 600;
  min-width: 120px;
}

.progress-fill {
  height: 100%;
  background: var(--primary);
  border-radius: 3px;
  transition: width 0.3s ease;
}

.console-output {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  margin-bottom: 16px;
}

.console-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-surface-alt);
  border-bottom: 1px solid var(--border);
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.log-mode-toggle {
  display: flex;
  gap: 4px;
}

.mode-btn {
  padding: 4px 10px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.mode-btn:hover {
  background: var(--bg-hover);
  border-color: var(--border-hover);
}

.mode-btn.active {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}

.btn-clear {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 0.75rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-clear:hover {
  background: var(--bg-hover);
  border-color: var(--border-hover);
}

.btn-clear svg {
  width: 14px;
  height: 14px;
}

.console-body {
  height: 400px;
  overflow-y: auto;
  padding: 16px;
  font-family: 'Fira Code', monospace;
  font-size: 0.8125rem;
  line-height: 1.8;
  background: #1e1e1e;
  color: #d4d4d4;
}

.console-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: #666;
}

.console-empty svg {
  width: 48px;
  height: 48px;
  opacity: 0.5;
}

.log-line {
  white-space: pre-wrap;
  word-break: break-all;
}

.log-system {
  color: #4fc3f7;
}

.log-progress {
  color: #ffb74d;
}

.log-best {
  color: #66bb6a;
}

.log-generation {
  color: #81c784;
}

.log-error {
  color: #ef5350;
}

.log-warning {
  color: #ffb74d;
}

.console-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  margin-bottom: 16px;
}

.action-info {
  display: flex;
  align-items: center;
}

.info-warning,
.info-ready {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
}

.info-warning {
  color: var(--cta);
}

.info-ready {
  color: var(--secondary);
}

.info-warning svg,
.info-ready svg {
  width: 18px;
  height: 18px;
}

.action-buttons {
  display: flex;
  gap: 12px;
}

.btn-export-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.btn-export-step:hover {
  background: var(--bg-surface-alt);
  border-color: var(--primary-light);
  color: var(--primary);
}

.btn-export-step svg {
  width: 18px;
  height: 18px;
}

.btn-run {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 28px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.btn-run:hover:not(:disabled) {
  background: var(--primary-dark);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-run:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-run.running {
  background: var(--status-running);
}

.btn-run svg {
  width: 20px;
  height: 20px;
}

.btn-cancel {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 28px;
  background: var(--error);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.btn-cancel:hover {
  background: var(--error-dark, #dc2626);
  transform: translateY(-1px);
}

.btn-cancel svg {
  width: 20px;
  height: 20px;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.success-message {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid var(--secondary);
  border-radius: var(--radius-lg);
}

.success-message > svg {
  width: 32px;
  height: 32px;
  color: var(--secondary);
  flex-shrink: 0;
}

.success-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.success-title {
  font-weight: 600;
  color: var(--secondary);
}

.success-desc {
  font-size: 0.875rem;
  font-family: 'Fira Code', monospace;
  color: var(--text-secondary);
}

.btn-view-results {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--secondary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.btn-view-results:hover {
  background: var(--secondary-light);
  transform: translateY(-1px);
}

.btn-view-results svg {
  width: 16px;
  height: 16px;
}
</style>
