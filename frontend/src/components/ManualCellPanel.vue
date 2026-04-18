<template>
  <div class="manual-cell-panel">
    <div class="page-header">
      <h2>{{ t('manual.title') }}</h2>
      <p>{{ t('manual.subtitle') }}</p>
    </div>

    <div class="manual-form">
      <div v-for="(group, idx) in groups" :key="idx" class="group-card">
        <div class="group-header">
          <span class="group-index">{{ t('manual.group', { index: idx + 1 }) }}</span>
          <button v-if="groups.length > 1" class="btn-remove" @click="removeGroup(idx)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <div class="cell-inputs">
          <div class="input-group">
            <label>a (Å)</label>
            <input type="number" v-model.number="group.a" step="0.001" min="0.01" />
          </div>
          <div class="input-group">
            <label>b (Å)</label>
            <input type="number" v-model.number="group.b" step="0.001" min="0.01" />
          </div>
          <div class="input-group">
            <label>c (Å)</label>
            <input type="number" v-model.number="group.c" step="0.001" min="0.01" />
          </div>
          <div class="input-group">
            <label>α (°)</label>
            <input type="number" v-model.number="group.alpha" step="0.01" min="0.01" max="180" />
          </div>
          <div class="input-group">
            <label>β (°)</label>
            <input type="number" v-model.number="group.beta" step="0.01" min="0.01" max="180" />
          </div>
          <div class="input-group">
            <label>γ (°)</label>
            <input type="number" v-model.number="group.gamma" step="0.01" min="0.01" max="180" />
          </div>
          <div class="input-group">
            <label>Wavelength (Å)</label>
            <input type="number" v-model.number="group.wavelength" step="0.001" min="0.01" />
          </div>
        </div>
      </div>

      <button class="btn-add" @click="addGroup">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        {{ t('manual.addGroup') }}
      </button>

      <div class="actions-row">
        <button class="btn-generate" @click="generate" :disabled="generating">
          <svg v-if="!generating" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="7,10 12,15 17,10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          <span v-if="generating" class="spinner"></span>
          {{ generating ? t('manual.generating') : t('manual.generate', { count: groups.length, plural: groups.length > 1 ? 's' : '' }) }}
        </button>
      </div>
    </div>

    <div v-if="error" class="error-banner">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="15" y1="9" x2="9" y2="15"/>
        <line x1="9" y1="9" x2="15" y2="15"/>
      </svg>
      <span>{{ error }}</span>
    </div>

    <div v-if="batchResults.length" class="results-section">
      <div v-for="(res, idx) in batchResults" :key="idx" class="result-card">
        <div v-if="res.success" class="result-success">
          <div class="result-header">
            <span class="group-badge">{{ res.data?.label || res.label || `${t('manual.group', { index: idx + 1 })}` }}</span>
            <span class="reflection-count">{{ res.data?.totalReflections ?? 0 }} {{ t('manual.reflections') }}</span>
          </div>

          <div v-if="res.data?.volume" class="volume-info">
            <span class="volume-label">{{ t('manual.volume') }}</span>
            <span class="volume-value">{{ res.data.volume.toFixed(3) }} Å³</span>
          </div>

          <div v-if="res.data?.cellParams" class="cell-info">
            <span class="cell-label">{{ t('manual.cell') }}</span>
            <span class="cell-value">
              {{ res.data.cellParams.a.toFixed(3) }}, {{ res.data.cellParams.b.toFixed(3) }}, {{ res.data.cellParams.c.toFixed(3) }},
              {{ res.data.cellParams.alpha.toFixed(2) }}, {{ res.data.cellParams.beta.toFixed(2) }}, {{ res.data.cellParams.gamma.toFixed(2) }}
            </span>
          </div>

          <button class="btn-download" @click="downloadResult(res.data, idx)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
              <polyline points="7,10 12,15 17,10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            {{ t('manual.download') }}
          </button>
        </div>
        <div v-else class="result-failed">
          <span class="failed-label">{{ res.label || `${t('manual.group', { index: idx + 1 })}` }}</span>
          <span class="failed-msg">{{ res.message || t('manual.generationFailed') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/index'

const { t } = useI18n()

const defaultGroup = () => ({
  a: 7.40, b: 4.93, c: 2.54,
  alpha: 90.0, beta: 90.0, gamma: 90.0,
  wavelength: 1.542
})

const groups = reactive([defaultGroup()])
const generating = ref(false)
const error = ref(null)
const batchResults = ref([])

const addGroup = () => {
  groups.push(defaultGroup())
}

const removeGroup = (idx) => {
  groups.splice(idx, 1)
}

const generate = async () => {
  error.value = null
  batchResults.value = []
  generating.value = true

  try {
    const payload = groups.map((g, idx) => ({
      label: `manual_${String(idx + 1).padStart(2, '0')}`,
      a: g.a, b: g.b, c: g.c,
      alpha: g.alpha, beta: g.beta, gamma: g.gamma,
      wavelength: g.wavelength,
    }))

    const res = await api.manualBatchFullmiller(payload)
    if (Array.isArray(res.data) && res.data.length > 0) {
      batchResults.value = res.data.map((item, i) => ({
        ...item,
        label: item.label || item.data?.label || payload[i]?.label || `${t('manual.group', { index: i + 1 })}`,
      }))
      if (!res.success) {
        error.value = res.message || t('manual.someGroupsFailed')
      }
    } else {
      error.value = res.message || t('manual.generationFailed')
    }
  } catch (e) {
    error.value = e.message || t('manual.requestFailed')
  } finally {
    generating.value = false
  }
}

const downloadResult = (data, idx) => {
  if (!data.fullMillerContent) return
  const blob = new Blob([data.fullMillerContent], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `FullMiller_${data.label || `group_${idx + 1}`}.txt`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.manual-cell-panel {
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

.manual-form {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 20px;
}

.group-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 12px;
  background: var(--bg-surface-alt);
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.group-index {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--primary);
}

.btn-remove {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.btn-remove:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: #EF4444;
  color: #EF4444;
}

.cell-inputs {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 16px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-group label {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.input-group input {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-family: 'Fira Code', monospace;
  background: var(--bg-surface);
  color: var(--text-primary);
  transition: border-color var(--transition-fast);
}

.input-group input:focus {
  outline: none;
  border-color: var(--primary);
}

.btn-add {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--bg-surface-alt);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-bottom: 16px;
}

.btn-add:hover {
  background: var(--bg-hover);
  border-color: var(--primary);
  color: var(--primary);
}

.actions-row {
  display: flex;
  justify-content: flex-end;
}

.btn-generate {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.btn-generate:hover:not(:disabled) {
  background: var(--primary-dark);
  transform: translateY(-1px);
}

.btn-generate:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-generate svg {
  width: 18px;
  height: 18px;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--status-error);
  border-radius: var(--radius-lg);
  color: var(--status-error);
  font-weight: 500;
  margin-bottom: 20px;
}

.error-banner svg {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.results-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.result-success {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.group-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--primary-bg);
  color: var(--primary);
  font-size: 0.8125rem;
  font-weight: 700;
}

.reflection-count {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.volume-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-md);
}

.volume-label {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.volume-value {
  font-size: 1rem;
  font-weight: 700;
  font-family: 'Fira Code', monospace;
  color: var(--primary);
}

.cell-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.cell-label {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.cell-value {
  font-family: 'Fira Code', monospace;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--primary);
}

.btn-download {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: var(--bg-surface);
  border: 1px solid var(--primary);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--primary);
  cursor: pointer;
  transition: all var(--transition-normal);
  align-self: flex-start;
}

.btn-download:hover {
  background: var(--primary-bg);
  transform: translateY(-1px);
}

.btn-download svg {
  width: 16px;
  height: 16px;
}

.result-failed {
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.failed-label {
  font-weight: 600;
  color: var(--text-primary);
}

.failed-msg {
  font-size: 0.875rem;
  color: var(--status-error);
}
</style>
