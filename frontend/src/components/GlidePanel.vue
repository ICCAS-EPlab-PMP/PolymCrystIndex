<template>
  <div class="glide-panel">
    <div class="page-header">
      <h2>{{ t('glide.title') }}</h2>
      <p>{{ t('glide.subtitle') }}</p>
    </div>

    <div class="glide-form">
      <div class="form-section">
        <h3>{{ t('glide.baseCellParams') }}</h3>
        <div class="cell-inputs">
          <div class="input-group">
            <label>a (Å)</label>
            <input type="number" v-model.number="baseCell.a" step="0.001" min="0.01" />
          </div>
          <div class="input-group">
            <label>b (Å)</label>
            <input type="number" v-model.number="baseCell.b" step="0.001" min="0.01" />
          </div>
          <div class="input-group">
            <label>c (Å)</label>
            <input type="number" v-model.number="baseCell.c" step="0.001" min="0.01" />
          </div>
          <div class="input-group">
            <label>α (°)</label>
            <input type="number" v-model.number="baseCell.alpha" step="0.01" min="0.01" max="180" />
          </div>
          <div class="input-group">
            <label>β (°)</label>
            <input type="number" v-model.number="baseCell.beta" step="0.01" min="0.01" max="180" />
          </div>
          <div class="input-group">
            <label>γ (°)</label>
            <input type="number" v-model.number="baseCell.gamma" step="0.01" min="0.01" max="180" />
          </div>
          <div class="input-group">
            <label>Wavelength (Å)</label>
            <input type="number" v-model.number="baseCell.wavelength" step="0.001" min="0.01" />
          </div>
        </div>
      </div>

      <div class="form-section">
        <h3>{{ t('glide.glideShearGroups') }}</h3>
        <div v-for="(group, idx) in glideGroups" :key="idx" class="glide-group-row">
          <div class="input-group">
            <label>{{ t('glide.label') }}</label>
            <input type="text" v-model="group.label" :placeholder="t('glide.labelPlaceholder')" />
          </div>
          <div class="input-group" :title="t('glide.nATip')">
            <label>{{ t('glide.nA') }} <span class="hint-icon" :title="t('glide.nATip')">ⓘ</span></label>
            <input type="number" v-model.number="group.nA" step="1" @change="enforceInt(group, 'nA')" />
          </div>
          <div class="input-group" :title="t('glide.nBTip')">
            <label>{{ t('glide.nB') }} <span class="hint-icon" :title="t('glide.nBTip')">ⓘ</span></label>
            <input type="number" v-model.number="group.nB" step="1" @change="enforceInt(group, 'nB')" />
          </div>
          <div class="input-group" :title="t('glide.l0Tip')">
            <label>{{ t('glide.l0') }} <span class="hint-icon" :title="t('glide.l0Tip')">ⓘ</span></label>
            <input type="number" v-model.number="group.l0" step="1" @change="enforceInt(group, 'l0')" />
          </div>
          <button class="glide-remove-btn" @click="removeGroup(idx)" :title="t('glide.removeGroup')">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <button class="btn-add-group" @click="addGroup">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          {{ t('glide.addGroup') }}
        </button>
      </div>

      <button class="btn-generate" @click="generate" :disabled="generating">
        <svg v-if="!generating" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>
          <line x1="4" y1="22" x2="4" y2="15"/>
        </svg>
        <span v-if="generating" class="spinner"></span>
        {{ generating ? t('glide.generating') : t('glide.generate') }}
      </button>
    </div>

    <div v-if="error" class="error-banner">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="15" y1="9" x2="9" y2="15"/>
        <line x1="9" y1="9" x2="15" y2="15"/>
      </svg>
      <span>{{ error }}</span>
    </div>

    <div v-if="results" class="results-section">
      <div class="success-banner">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
          <polyline points="22,4 12,14.01 9,11.01"/>
        </svg>
        <span>{{ t('glide.analysisComplete', { count: results.glideBatchOutputs.groups.length }) }}</span>
      </div>

      <div v-if="results.baseCell" class="base-cell-info">
        <span class="info-label">{{ t('glide.baseCell') }}</span>
        <span class="info-value">
          {{ results.baseCell.a.toFixed(3) }}, {{ results.baseCell.b.toFixed(3) }}, {{ results.baseCell.c.toFixed(3) }},
          {{ results.baseCell.alpha.toFixed(2) }}, {{ results.baseCell.beta.toFixed(2) }}, {{ results.baseCell.gamma.toFixed(2) }}
        </span>
      </div>

      <div v-for="group in results.glideBatchOutputs.groups" :key="group.label" class="glide-result-card">
        <div class="glide-result-header">
          <span class="group-badge">{{ group.label }}</span>
          <span class="glide-input-info" v-if="group.input">
            nA={{ group.input.nA }}, nB={{ group.input.nB }}, l₀={{ group.input.l0 }}
          </span>
        </div>
        <div class="glide-result-body">
          <div v-if="group.cellParams" class="cell-info">
            <span class="cell-label">{{ t('glide.cell') }}:</span>
            <span class="cell-value">
              {{ group.cellParams.a.toFixed(3) }}, {{ group.cellParams.b.toFixed(3) }}, {{ group.cellParams.c.toFixed(3) }},
              {{ group.cellParams.alpha.toFixed(2) }}, {{ group.cellParams.beta.toFixed(2) }}, {{ group.cellParams.gamma.toFixed(2) }}
            </span>
          </div>
          <div v-if="group.volume !== null && group.volume !== undefined" class="cell-info">
            <span class="cell-label">{{ t('glide.volume') }}:</span>
            <span class="cell-value">{{ group.volume.toFixed(3) }} Å³</span>
          </div>
          <div class="reflection-info">
            {{ group.totalReflections }} {{ t('glide.reflections') }}
          </div>
          <button class="btn-download-sm" @click="downloadGroup(group)">{{ t('glide.download') }}</button>
        </div>
      </div>

      <div v-if="hasBrowsableGroups" class="quick-browse-section">
        <button class="quick-browse-toggle" @click="toggleBrowseExpanded">
          <svg class="chevron-icon" :class="{ expanded: browseExpanded }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6,9 12,15 18,9"/>
          </svg>
          {{ browseExpanded ? t('glide.quickBrowseCollapse') : t('glide.quickBrowseExpand') }}
        </button>

        <div v-if="browseExpanded" class="quick-browse-content">
          <div class="browse-mode-switch">
            <label class="mode-option">
              <input v-model="browseMode" type="radio" value="single" />
              <span>{{ t('glide.browseModeSingle') }}</span>
            </label>
            <label class="mode-option">
              <input v-model="browseMode" type="radio" value="overlay" />
              <span>{{ t('glide.browseModeOverlay') }}</span>
            </label>
          </div>

          <div v-if="browseMode === 'single'" class="selection-panel">
            <label class="selection-label">{{ t('glide.selectGroup') }}</label>
            <select v-model="selectedSingleLabel" class="group-select">
              <option v-for="group in browsableGroups" :key="group.label" :value="group.label">
                {{ group.label }} · {{ group.totalReflections || 0 }}
              </option>
            </select>
          </div>

          <div v-else class="selection-panel">
            <label class="selection-label">{{ t('glide.overlaySelectionTitle') }}</label>
            <p class="quick-browse-hint">{{ t('glide.overlayHint') }}</p>
            <div class="overlay-checklist">
              <label v-for="group in browsableGroups" :key="group.label" class="overlay-item" :class="{ active: selectedOverlayLabels.includes(group.label) }">
                <input
                  type="checkbox"
                  :checked="selectedOverlayLabels.includes(group.label)"
                  :disabled="!selectedOverlayLabels.includes(group.label) && selectedOverlayLabels.length >= 5"
                  @change="toggleOverlayGroup(group.label)"
                />
                <span>{{ group.label }}</span>
                <span class="chip-count">{{ group.totalReflections || 0 }}</span>
              </label>
            </div>
            <span class="overlay-limit">{{ t('glide.selectedCount', { count: selectedGroups.length }) }}</span>
            <span v-if="selectedOverlayLabels.length >= 5" class="overlay-limit warning">{{ t('glide.overlayLimit') }}</span>
          </div>

          <p class="quick-browse-hint">{{ t('glide.liveSyncHint') }}</p>

          <div v-if="selectedGroups.length > 0" class="shared-visualizer">
            <Visualizer
              resultType="glide"
              :overlayGroups="selectedGroups"
              :importRequestKey="importSelectionKey"
              @raw-session-ready="handleVisualizerReady"
              compact
            />
          </div>
          <p v-else class="quick-browse-empty">{{ t('glide.selectGroup') }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { api } from '@/api/index'
import Visualizer from '@/components/Visualizer.vue'

const { t } = useI18n()

const baseCell = reactive({
  a: 7.40,
  b: 4.93,
  c: 2.54,
  alpha: 90.0,
  beta: 90.0,
  gamma: 90.0,
  wavelength: 1.542
})

const glideGroups = reactive([
  { label: '', nA: 1, nB: 0, l0: 1 }
])

const generating = ref(false)
const error = ref(null)
const results = ref(null)
const browseExpanded = ref(false)
const keepBrowseExpanded = ref(false)
const browseMode = ref('single')
const selectedSingleLabel = ref('')
const selectedOverlayLabels = ref([])
const importSelectionKey = ref(0)
const visualizerReady = ref(false)

const browsableGroups = computed(() => {
  const groups = results.value?.glideBatchOutputs?.groups || []
  return groups
    .filter(g => (g.workDir || g.fullMillerContent))
    .map(g => ({
      label: g.label,
      fullMillerContent: g.fullMillerContent || '',
      workDir: g.workDir || '',
      totalReflections: g.totalReflections || 0,
    }))
})

const selectedGroups = computed(() => {
  if (browseMode.value === 'overlay') {
    return browsableGroups.value.filter(group => selectedOverlayLabels.value.includes(group.label)).slice(0, 5)
  }
  return browsableGroups.value.filter(group => group.label === selectedSingleLabel.value).slice(0, 1)
})

const hasBrowsableGroups = computed(() => {
  return browsableGroups.value.length > 0
})

const toggleOverlayGroup = (label) => {
  if (selectedOverlayLabels.value.includes(label)) {
    selectedOverlayLabels.value = selectedOverlayLabels.value.filter(item => item !== label)
    return
  }
  if (selectedOverlayLabels.value.length >= 5) return
  selectedOverlayLabels.value = [...selectedOverlayLabels.value, label]
}

const toggleBrowseExpanded = () => {
  browseExpanded.value = !browseExpanded.value
  if (!browseExpanded.value) {
    keepBrowseExpanded.value = false
  }
}

const handleVisualizerReady = () => {
  visualizerReady.value = true
  if (selectedGroups.value.length > 0) {
    importSelectionKey.value += 1
  }
}

watch(selectedGroups, (groups, previousGroups) => {
  if (!visualizerReady.value || groups.length === 0) return
  const currentKey = groups.map(group => group.label).join('|')
  const previousKey = (previousGroups || []).map(group => group.label).join('|')
  if (currentKey !== previousKey) {
    importSelectionKey.value += 1
  }
})

watch([
  () => browsableGroups.value.length,
  browseMode,
  selectedSingleLabel,
  selectedOverlayLabels,
], ([count]) => {
  if (count === 0) {
    browseExpanded.value = false
    keepBrowseExpanded.value = false
    return
  }
  if (keepBrowseExpanded.value && !browseExpanded.value) {
    browseExpanded.value = true
  }
}, { deep: true })

/** Force a field to integer */
const enforceInt = (group, field) => {
  if (group[field] == null || Number.isNaN(group[field])) {
    group[field] = 0
  } else {
    group[field] = Math.round(group[field])
  }
}

const addGroup = () => {
  glideGroups.push({ label: '', nA: 0, nB: 0, l0: 1 })
}

const removeGroup = (idx) => {
  if (glideGroups.length > 1) {
    glideGroups.splice(idx, 1)
  }
}

const generate = async () => {
  error.value = null
  generating.value = true

  const validGroups = glideGroups.filter(g => Math.round(g.l0) !== 0)
  if (validGroups.length === 0) {
    error.value = t('glide.errorNoGroup')
    generating.value = false
    return
  }

  // Ensure integer values for nA, nB, l0
  const intGroups = validGroups.map(g => ({
    ...g,
    nA: Math.round(g.nA),
    nB: Math.round(g.nB),
    l0: Math.round(g.l0),
  }))

  try {
    const res = await api.glideBatchFullmiller(
      baseCell.a, baseCell.b, baseCell.c,
      baseCell.alpha, baseCell.beta, baseCell.gamma,
      baseCell.wavelength,
      intGroups
    )
    if (res.success && res.data) {
      results.value = res.data
      const firstGroup = res.data?.glideBatchOutputs?.groups?.find(g => g.workDir || g.fullMillerContent)
      selectedSingleLabel.value = firstGroup?.label || ''
      selectedOverlayLabels.value = firstGroup?.label ? [firstGroup.label] : []
      browseMode.value = 'single'
      keepBrowseExpanded.value = true
      browseExpanded.value = true
      if (visualizerReady.value && firstGroup) {
        importSelectionKey.value += 1
      } else {
        importSelectionKey.value = 0
      }
    } else {
      error.value = res.message || t('glide.generationFailed')
    }
  } catch (e) {
    error.value = e.message || t('glide.requestFailed')
  } finally {
    generating.value = false
  }
}

const downloadGroup = (group) => {
  if (!group.fullMillerContent) return
  const blob = new Blob([group.fullMillerContent], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `FullMiller_${group.label}.txt`
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.glide-panel {
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

.glide-form {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 24px;
  margin-bottom: 20px;
}

.form-section {
  margin-bottom: 20px;
}

.form-section h3 {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 12px;
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
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.hint-icon {
  font-size: 0.75rem;
  color: var(--text-muted);
  cursor: help;
  font-style: normal;
}

.input-group input {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-family: 'Fira Code', monospace;
  background: var(--bg-surface-alt);
  color: var(--text-primary);
  transition: border-color var(--transition-fast);
}

.input-group input:focus {
  outline: none;
  border-color: var(--primary);
}

.glide-group-row {
  display: grid;
  grid-template-columns: 1.2fr 0.7fr 0.7fr 0.7fr auto;
  gap: 8px;
  align-items: end;
  margin-bottom: 8px;
}

.glide-remove-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  cursor: pointer;
  color: var(--text-muted);
  transition: all var(--transition-fast);
}

.glide-remove-btn:hover {
  background: rgba(239, 68, 68, 0.1);
  border-color: #EF4444;
  color: #EF4444;
}

.btn-add-group {
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
}

.btn-add-group:hover {
  background: var(--bg-hover);
  border-color: var(--primary);
  color: var(--primary);
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
  border: 2px solid rgba(255, 255, 255, 0.3);
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
  gap: 16px;
}

.success-banner {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid var(--secondary);
  border-radius: var(--radius-lg);
  color: var(--secondary);
  font-weight: 600;
}

.success-banner svg {
  width: 20px;
  height: 20px;
}

.base-cell-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.info-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
  font-weight: 500;
}

.info-value {
  font-size: 1rem;
  font-weight: 700;
  font-family: 'Fira Code', monospace;
  color: var(--primary);
}

.glide-result-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.glide-result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-surface-alt);
  border-bottom: 1px solid var(--border);
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

.glide-input-info {
  font-family: 'Fira Code', monospace;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.glide-result-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
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

.reflection-info {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.btn-download-sm {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--bg-surface-alt);
  border: 1px solid var(--primary);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--primary);
  cursor: pointer;
  transition: all var(--transition-normal);
  align-self: flex-start;
}

.btn-download-sm:hover {
  background: var(--primary-bg);
  transform: translateY(-1px);
}

.quick-browse-section {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.quick-browse-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 12px 16px;
  background: transparent;
  border: none;
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--primary);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.quick-browse-toggle:hover {
  background: var(--bg-hover);
}

.chevron-icon {
  width: 16px;
  height: 16px;
  color: var(--text-muted);
  transition: transform var(--transition-normal);
}

.chevron-icon.expanded {
  transform: rotate(180deg);
}

.quick-browse-content {
  padding: 0 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.browse-mode-switch {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.mode-option {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-surface-alt);
  color: var(--text-primary);
}

.selection-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.selection-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.group-select {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-surface-alt);
  color: var(--text-primary);
}

.quick-browse-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin: 0;
}

.overlay-checklist {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.overlay-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--bg-surface-alt);
}

.overlay-item.active {
  border-color: var(--primary);
  background: var(--primary-bg);
}

.group-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.group-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: var(--bg-surface-alt);
  border: 1px solid var(--border);
  border-radius: 999px;
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.group-chip:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.group-chip.selected {
  background: var(--primary-bg);
  border-color: var(--primary);
  color: var(--primary);
  font-weight: 600;
}

.chip-count {
  font-size: 0.6875rem;
  color: var(--text-muted);
  font-weight: 400;
}

.group-chip.selected .chip-count {
  color: var(--primary);
}

.overlay-limit {
  font-size: 0.75rem;
  color: var(--cta);
  font-weight: 500;
}

.overlay-limit.warning {
  color: var(--status-warning, #f59e0b);
}

.shared-visualizer {
  margin-top: 4px;
}

.quick-browse-empty {
  font-size: 0.8125rem;
  color: var(--text-muted);
  text-align: center;
  padding: 12px 0;
  margin: 0;
}
</style>
