<template>
  <div class="params-setup">
    <div class="page-header">
      <h2>{{ t('params.title') }}</h2>
      <p>{{ t('params.subtitle') }}</p>
    </div>

    <div class="params-grid">
      <div class="param-section">
        <div class="section-header" @click="expandedSections.ga = !expandedSections.ga">
          <div class="section-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
            <h3>{{ t('params.gaParams') }}</h3>
          </div>
          <svg class="chevron" :class="{ expanded: expandedSections.ga }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6,9 12,15 18,9"/>
          </svg>
        </div>
        <div class="section-content" :class="{ collapsed: !expandedSections.ga }">
          <div class="param-row">
            <div class="param-group">
              <label>{{ t('params.steps') }}</label>
              <input type="number" v-model.number="localParams.steps" min="5" />
              <span class="param-hint">{{ t('params.stepsHint') }}</span>
            </div>
            <div class="param-group">
              <label>{{ t('params.generations') }}</label>
              <input type="number" v-model.number="localParams.generations" min="10" />
              <span class="param-hint">{{ t('params.generationsHint') }}</span>
            </div>
          </div>

          <div class="param-subgroup">
            <h4>{{ t('params.populationRatios') }}</h4>
            <div class="ratio-grid">
              <div class="ratio-item">
                <label>{{ t('params.live') }}</label>
                <input type="number" v-model.number="localParams.liveRatio" min="0" max="100" />
              </div>
              <div class="ratio-item">
                <label>{{ t('params.exchange') }}</label>
                <input type="number" v-model.number="localParams.exchangeRatio" min="0" max="100" />
              </div>
              <div class="ratio-item">
                <label>{{ t('params.mutate') }}</label>
                <input type="number" v-model.number="localParams.mutateRatio" min="0" max="100" />
              </div>
              <div class="ratio-item">
                <label>{{ t('params.newPop') }}</label>
                <input type="number" v-model.number="localParams.newRatio" min="0" max="100" />
              </div>
            </div>
            <div v-if="ratioSum !== 100" class="ratio-warning">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <line x1="12" y1="17" x2="12.01" y2="17"/>
              </svg>
              {{ t('params.ratioWarning', { sum: ratioSum }) }}
            </div>
          </div>

          <div class="param-subgroup">
            <h4>{{ t('params.hklExploration') }}</h4>
            <div class="radio-group">
              <label class="radio-item">
                <input type="radio" v-model="localParams.hklMode" value="Default" />
                <span class="radio-label">{{ t('params.hklDefault') }}</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="localParams.hklMode" value="Full" />
                <span class="radio-label">{{ t('params.hklFull') }}</span>
              </label>
              <label class="radio-item">
                <input type="radio" v-model="localParams.hklMode" value="Custom" />
                <span class="radio-label">{{ t('params.hklCustom') }}</span>
              </label>
            </div>
            <div v-if="localParams.hklMode === 'Custom'" class="custom-hkl">
              <div class="hkl-input">
                <label>{{ t('params.maxH') }}</label>
                <input type="number" v-model.number="localParams.custH" min="0" max="20" />
              </div>
              <div class="hkl-input">
                <label>{{ t('params.maxK') }}</label>
                <input type="number" v-model.number="localParams.custK" min="0" max="20" />
              </div>
              <div class="hkl-input">
                <label>{{ t('params.maxL') }}</label>
                <input type="number" v-model.number="localParams.custL" min="0" max="20" />
              </div>
            </div>
          </div>

          <div class="param-subgroup">
            <h4>{{ t('params.fixedPeakTitle') }}</h4>
            <label class="toggle-item">
              <input type="checkbox" v-model="localParams.fixModeEnabled" />
              <span class="toggle-label">{{ t('params.fixedPeakToggle') }}</span>
            </label>
            <div v-if="localParams.fixModeEnabled" class="param-group">
              <label for="fixed-peak-text">{{ t('params.fixedPeakFormatLabel') }}</label>
              <textarea
                id="fixed-peak-text"
                v-model="localParams.fixedPeakText"
                class="fixed-peak-textarea"
                spellcheck="false"
                :placeholder="t('params.fixedPeakPlaceholder')"
              />
              <span class="param-hint">{{ t('params.fixedPeakHint') }}</span>
              <span class="param-hint">{{ fixedPeakSummary }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="param-section">
        <div class="section-header" @click="expandedSections.cell = !expandedSections.cell">
          <div class="section-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
            </svg>
            <h3>{{ t('params.cellConstraints') }}</h3>
          </div>
          <svg class="chevron" :class="{ expanded: expandedSections.cell }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6,9 12,15 18,9"/>
          </svg>
        </div>
        <div class="section-content" :class="{ collapsed: !expandedSections.cell }">
          <div class="cell-params-layout">
            <div class="cell-row">
              <div class="cell-axis">
                <h4>{{ t('params.axisMinMax', { axis: 'a' }) }}</h4>
                <div class="axis-inputs">
                  <div class="axis-input">
                    <label>Min</label>
                    <input type="number" v-model.number="localParams.aMin" step="0.1" />
                  </div>
                  <div class="axis-input">
                    <label>Max</label>
                    <input type="number" v-model.number="localParams.aMax" step="0.1" />
                  </div>
                </div>
              </div>
              <div class="cell-axis">
                <h4>{{ t('params.angleMinMax', { angle: 'α' }) }}</h4>
                <div class="axis-inputs">
                  <div class="axis-input">
                    <label>Min</label>
                    <input type="number" v-model.number="localParams.alphaMin" step="1" />
                  </div>
                  <div class="axis-input">
                    <label>Max</label>
                    <input type="number" v-model.number="localParams.alphaMax" step="1" />
                  </div>
                </div>
              </div>
            </div>
            <div class="cell-row">
              <div class="cell-axis">
                <h4>{{ t('params.axisMinMax', { axis: 'b' }) }}</h4>
                <div class="axis-inputs">
                  <div class="axis-input">
                    <label>Min</label>
                    <input type="number" v-model.number="localParams.bMin" step="0.1" />
                  </div>
                  <div class="axis-input">
                    <label>Max</label>
                    <input type="number" v-model.number="localParams.bMax" step="0.1" />
                  </div>
                </div>
              </div>
              <div class="cell-axis">
                <h4>{{ t('params.angleMinMax', { angle: 'β' }) }}</h4>
                <div class="axis-inputs">
                  <div class="axis-input">
                    <label>Min</label>
                    <input type="number" v-model.number="localParams.betaMin" step="1" />
                  </div>
                  <div class="axis-input">
                    <label>Max</label>
                    <input type="number" v-model.number="localParams.betaMax" step="1" />
                  </div>
                </div>
              </div>
            </div>
            <div class="cell-row">
              <div class="cell-axis">
                <h4>{{ t('params.axisMinMax', { axis: 'c' }) }}</h4>
                <div class="axis-inputs">
                  <div class="axis-input">
                    <label>Min</label>
                    <input type="number" v-model.number="localParams.cMin" step="0.1" />
                  </div>
                  <div class="axis-input">
                    <label>Max</label>
                    <input type="number" v-model.number="localParams.cMax" step="0.1" />
                  </div>
                </div>
              </div>
              <div class="cell-axis">
                <h4>{{ t('params.angleMinMax', { angle: 'γ' }) }}</h4>
                <div class="axis-inputs">
                  <div class="axis-input">
                    <label>Min</label>
                    <input type="number" v-model.number="localParams.gammaMin" step="1" />
                  </div>
                  <div class="axis-input">
                    <label>Max</label>
                    <input type="number" v-model.number="localParams.gammaMax" step="1" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="param-section">
        <div class="section-header" @click="expandedSections.advanced = !expandedSections.advanced">
          <div class="section-title">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
            </svg>
            <h3>{{ t('params.advanced') }}</h3>
          </div>
          <svg class="chevron" :class="{ expanded: expandedSections.advanced }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6,9 12,15 18,9"/>
          </svg>
        </div>
        <div class="section-content" :class="{ collapsed: !expandedSections.advanced }">
          <div class="advanced-grid">
            <div class="param-group">
              <label>{{ t('params.wavelength') }}</label>
              <input type="number" v-model.number="localParams.wavelength" step="0.001" min="0.01" />
            </div>
            <div class="param-group">
              <label>{{ t('params.highSymmetry') }}</label>
              <input type="range" v-model.number="localParams.esym" min="0.5" max="1" step="0.01" />
              <span class="range-value">{{ localParams.esym.toFixed(2) }}</span>
            </div>
            <div class="param-group">
              <label>{{ t('params.ompThreads') }}</label>
              <input type="number" v-model.number="localParams.ompThreads" min="1" :max="effectiveOmpMax" />
              <span v-if="adminMaxOmpThreads" class="param-hint">{{ t('admin.ompLimitHint', { n: adminMaxOmpThreads }) }}</span>
            </div>
          </div>

          <div class="weight-factors">
            <h4>{{ t('params.weightFactors') }}</h4>
            <div class="weight-grid">
              <div class="weight-item">
                <label>{{ t('params.azimuth') }}</label>
                <input type="number" v-model.number="localParams.e1" step="0.1" />
              </div>
              <div class="weight-item">
                <label>{{ t('params.qValue') }}</label>
                <input type="number" v-model.number="localParams.e2" step="0.1" />
              </div>
              <div class="weight-item">
                <label>{{ t('params.volume') }}</label>
                <input type="number" v-model.number="localParams.e3" step="0.1" />
              </div>
            </div>
          </div>

          <div class="toggles">
            <label class="toggle-item">
              <input type="checkbox" v-model="localParams.lmMode" />
              <span class="toggle-label">{{ t('params.lmOptimization') }}</span>
            </label>
            <label class="toggle-item">
              <input type="checkbox" v-model="localParams.tiltCheck" />
              <span class="toggle-label">{{ t('params.tiltOpt') }}</span>
            </label>
          </div>

          <div class="special-functions">
            <h4>{{ t('params.specialFunctions') }}</h4>
            <label class="toggle-item">
              <input type="checkbox" v-model="localParams.pseuOrth" />
              <span class="toggle-label">{{ t('params.pseudoOrth') }}</span>
            </label>

            <label class="toggle-item disabled-toggle" aria-disabled="true">
              <input type="checkbox" :checked="false" disabled />
              <span class="toggle-label">{{ t('params.peakSymmetryMode') }}</span>
            </label>
            <div class="peak-symmetry-thresholds disabled-thresholds">
              <div class="weight-item">
                <label>{{ t('params.peakSymmetryTq') }}</label>
                <input type="number" :value="defaultParams.symmetryTq" step="0.01" min="0" disabled />
                <p class="threshold-hint">{{ t('params.peakSymmetryTqHint') }}</p>
              </div>
              <div class="weight-item">
                <label>{{ t('params.peakSymmetryTa') }}</label>
                <input type="number" :value="defaultParams.symmetryTa" step="0.1" min="0" disabled />
                <p class="threshold-hint">{{ t('params.peakSymmetryTaHint') }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="actions-bar">
      <p v-if="saveNotice" class="save-notice" role="status" aria-live="polite">
        {{ saveNotice }}
      </p>

      <div class="actions">
      <button class="btn-secondary" @click="resetParams">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="1,4 1,10 7,10"/>
          <path d="M3.51 15a9 9 0 102.13-9.36L1 10"/>
        </svg>
        {{ t('params.resetDefaults') }}
      </button>
      <button class="btn-primary" @click="saveParams">
        {{ t('params.saveParams') }}
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/>
          <polyline points="17,21 17,13 7,13 7,21"/>
          <polyline points="7,3 7,8 15,8"/>
        </svg>
      </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, watch, ref, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/index'

const { t } = useI18n()
const props = defineProps({
  params: {
    type: Object,
    required: true
  }
})

const defaultParams = {
  steps: 30,
  generations: 2000,
  liveRatio: 10,
  exchangeRatio: 20,
  mutateRatio: 50,
  newRatio: 20,
  aMin: 3.0,
  aMax: 10.0,
  bMin: 3.0,
  bMax: 10.0,
  cMin: 5.0,
  cMax: 15.0,
  alphaMin: 60,
  alphaMax: 150,
  betaMin: 60,
  betaMax: 150,
  gammaMin: 60,
  gammaMax: 150,
  e1: 1.0,
  e2: 100.0,
  e3: 500.0,
  e4: 1.0,
  wavelength: 1.542,
  esym: 0.95,
  duplicate: false,
  lmMode: true,
  tiltCheck: false,
  pseuOrth: false,
  peakSymmetryEnabled: false,
  symmetryTq: 0.02,
  symmetryTa: 1.0,
  mergeGradientEnabled: false,
  mergeGradientThreshold: 0.0,
  hklMode: 'Default',
  custH: 5,
  custK: 5,
  custL: 0,
  fixModeEnabled: false,
  fixedPeakText: '',
  ompThreads: 1,
  glideBatches: []
}

const localParams = reactive({ ...props.params })
localParams.peakSymmetryEnabled = false
localParams.symmetryTq = defaultParams.symmetryTq
localParams.symmetryTa = defaultParams.symmetryTa
const expandedSections = reactive({
  ga: true,
  cell: true,
  advanced: true
})

const adminMaxOmpThreads = ref(null)
const saveNotice = ref('')
let saveNoticeTimer = null

const effectiveOmpMax = computed(() => adminMaxOmpThreads.value || 256)

const fetchAdminOmpLimit = async () => {
  try {
    const result = await api.getServerStatus()
    if (result.success && result.data.maxOmpThreads) {
      adminMaxOmpThreads.value = result.data.maxOmpThreads
    }
  } catch (e) {
    // Silently fail - admin limit hint is optional
  }
}

onMounted(() => {
  fetchAdminOmpLimit()
})

onBeforeUnmount(() => {
  if (saveNoticeTimer) {
    clearTimeout(saveNoticeTimer)
  }
})

watch(() => props.params, (newParams) => {
  Object.assign(localParams, newParams)
  localParams.peakSymmetryEnabled = false
  localParams.symmetryTq = defaultParams.symmetryTq
  localParams.symmetryTa = defaultParams.symmetryTa
}, { deep: true })

watch(adminMaxOmpThreads, (maxThreads) => {
  if (maxThreads && localParams.ompThreads > maxThreads) {
    localParams.ompThreads = maxThreads
  }
})

watch(() => localParams.ompThreads, (value) => {
  const limit = effectiveOmpMax.value
  if (typeof value === 'number' && value > limit) {
    localParams.ompThreads = limit
  }
})

watch(() => localParams.symmetryTq, (value) => {
  if (typeof value !== 'number' || Number.isNaN(value) || value < 0) {
    localParams.symmetryTq = defaultParams.symmetryTq
  }
})

watch(() => localParams.symmetryTa, (value) => {
  if (typeof value !== 'number' || Number.isNaN(value) || value < 0) {
    localParams.symmetryTa = defaultParams.symmetryTa
  }
})

watch(() => localParams.mergeGradientThreshold, (value) => {
  if (typeof value !== 'number' || Number.isNaN(value) || value < 0) {
    localParams.mergeGradientThreshold = defaultParams.mergeGradientThreshold
  }
})

const ratioSum = computed(() => {
  return localParams.liveRatio + localParams.exchangeRatio + localParams.mutateRatio + localParams.newRatio
})

const fixedPeakCount = computed(() => {
  const text = typeof localParams.fixedPeakText === 'string' ? localParams.fixedPeakText : ''
  return text
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean)
    .length
})

const fixedPeakSummary = computed(() => {
  return fixedPeakCount.value > 0
    ? t('params.fixedPeakSummaryReady', { count: fixedPeakCount.value })
    : t('params.fixedPeakSummaryEmpty')
})

const resetParams = () => {
  Object.assign(localParams, defaultParams)
  localParams.peakSymmetryEnabled = false
}

const saveParams = () => {
  localParams.peakSymmetryEnabled = false
  localParams.symmetryTq = defaultParams.symmetryTq
  localParams.symmetryTa = defaultParams.symmetryTa
  Object.assign(props.params, localParams)
  saveNotice.value = t('params.saved')
  if (typeof window !== 'undefined') {
    window.$toast?.(saveNotice.value)
  }
  if (saveNoticeTimer) {
    clearTimeout(saveNoticeTimer)
  }
  saveNoticeTimer = setTimeout(() => {
    saveNotice.value = ''
    saveNoticeTimer = null
  }, 3000)
}
</script>

<style scoped>
.params-setup {
  max-width: 1000px;
}

.page-header {
  margin-bottom: 32px;
}

.disabled-toggle,
.disabled-thresholds {
  opacity: 0.55;
}

.page-header h2 {
  font-size: 1.75rem;
  margin-bottom: 8px;
}

.page-header p {
  color: var(--text-secondary);
}

.params-grid {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-bottom: 32px;
}

.param-section {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.section-header:hover {
  background: var(--bg-hover);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-title svg {
  width: 20px;
  height: 20px;
  color: var(--primary);
}

.section-title h3 {
  font-size: 1rem;
  font-weight: 600;
}

.chevron {
  width: 20px;
  height: 20px;
  color: var(--text-muted);
  transition: transform var(--transition-normal);
}

.chevron.expanded {
  transform: rotate(180deg);
}

.section-content {
  padding: 0 20px 20px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-height: 1000px;
  overflow: hidden;
  transition: all var(--transition-slow);
}

.section-content.collapsed {
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
  opacity: 0;
}

.param-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
}

.param-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.param-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
}

.param-group input[type="number"],
.param-group input[type="text"],
.fixed-peak-textarea {
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-family: 'Fira Code', monospace;
  transition: border-color var(--transition-fast);
}

.param-group input:focus {
  outline: none;
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px var(--primary-bg);
}

.fixed-peak-textarea {
  min-height: 120px;
  resize: vertical;
  line-height: 1.5;
}

.fixed-peak-textarea:focus {
  outline: none;
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px var(--primary-bg);
}

.param-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.param-subgroup {
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.param-subgroup h4 {
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text-secondary);
}

.ratio-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.ratio-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ratio-item label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.ratio-item input {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-family: 'Fira Code', monospace;
  text-align: center;
}

.ratio-warning {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding: 8px 12px;
  background: rgba(245, 158, 11, 0.1);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  color: var(--cta);
}

.ratio-warning svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.radio-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.radio-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.radio-item input {
  width: 16px;
  height: 16px;
  accent-color: var(--primary);
}

.radio-label {
  font-size: 0.875rem;
}

.custom-hkl {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}

.hkl-input {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hkl-input label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.hkl-input input {
  width: 80px;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-family: 'Fira Code', monospace;
  text-align: center;
}

.cell-params {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.cell-params-layout {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.cell-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

@media (max-width: 768px) {
  .cell-row {
    grid-template-columns: 1fr;
  }
}

.cell-axis h4 {
  font-size: 0.8125rem;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--text-secondary);
}

.axis-inputs {
  display: flex;
  gap: 8px;
}

.axis-input {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.axis-input label {
  font-size: 0.6875rem;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.axis-input input {
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-family: 'Fira Code', monospace;
  text-align: center;
}

.advanced-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.advanced-grid .param-group {
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
}

.advanced-grid .param-group label {
  flex-shrink: 0;
}

.advanced-grid input[type="number"] {
  width: 100px;
  padding: 8px;
  text-align: right;
}

.advanced-grid input[type="range"] {
  width: 120px;
  accent-color: var(--primary);
}

.range-value {
  font-family: 'Fira Code', monospace;
  font-size: 0.875rem;
  color: var(--primary);
  min-width: 40px;
  text-align: right;
}

.weight-factors {
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.weight-factors h4 {
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text-secondary);
}

.weight-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.weight-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.weight-item label {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.weight-item input {
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-family: 'Fira Code', monospace;
}

.toggles {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.special-functions {
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.special-functions h4 {
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text-secondary);
}

.peak-symmetry-config {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.peak-symmetry-thresholds {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.threshold-hint {
  margin: 4px 0 0;
  font-size: 0.6875rem;
  color: var(--text-muted);
}

.threshold-group input[type="number"] {
  width: 100%;
}

.toggle-item {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.toggle-item input {
  width: 18px;
  height: 18px;
  accent-color: var(--primary);
}

.toggle-label {
  font-size: 0.875rem;
}

.actions-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.save-notice {
  margin: 0;
  color: var(--success, #15803d);
  font-size: 0.9375rem;
  font-weight: 600;
}

.btn-secondary,
.btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.btn-secondary {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  color: var(--text-secondary);
}

.btn-secondary:hover {
  background: var(--bg-surface-alt);
  border-color: var(--border-hover);
  color: var(--text-primary);
}

.btn-primary {
  background: var(--primary);
  border: none;
  color: white;
}

.btn-primary:hover {
  background: var(--primary-dark);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-secondary svg,
.btn-primary svg {
  width: 18px;
  height: 18px;
}
</style>
