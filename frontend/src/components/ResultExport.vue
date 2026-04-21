<template>
  <div class="result-export">
    <div class="page-header">
      <h2>{{ t('results.title') }}</h2>
      <p>{{ t('results.subtitle') }}</p>
    </div>

    <div v-if="!hasResults" class="no-results">
      <div class="no-results-icon">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
          <polyline points="3.27,6.96 12,12.01 20.73,6.96"/>
          <line x1="12" y1="22.08" x2="12" y2="12"/>
        </svg>
      </div>
      <h3>{{ t('results.noResults') }}</h3>
      <p v-if="!isExternalResult">{{ t('results.noResultsDesc') }}</p>
      <p v-else>{{ t('results.noResultsDesc') }}</p>
      <button v-if="!isExternalResult" class="btn-start" @click="startAnalysis">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="5,3 19,12 5,21 5,3"/>
        </svg>
        {{ t('results.startAnalysis') }}
      </button>
    </div>

    <div v-else class="results-content">
      <div class="success-banner">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
          <polyline points="22,4 12,14.01 9,11.01"/>
        </svg>
        <span>{{ t('results.analysisComplete') }}</span>
      </div>

      <div class="results-grid">
        <div class="cell-params-card">
          <h3>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
            </svg>
            {{ t('results.unitCellParams') }}
          </h3>
          <div class="params-grid">
            <div class="param-item">
              <span class="param-label">a</span>
              <span class="param-value">{{ cellParams.a.toFixed(3) }}</span>
              <span class="param-unit">Å</span>
            </div>
            <div class="param-item">
              <span class="param-label">b</span>
              <span class="param-value">{{ cellParams.b.toFixed(3) }}</span>
              <span class="param-unit">Å</span>
            </div>
            <div class="param-item">
              <span class="param-label">c</span>
              <span class="param-value">{{ cellParams.c.toFixed(3) }}</span>
              <span class="param-unit">Å</span>
            </div>
            <div class="param-item">
              <span class="param-label">α</span>
              <span class="param-value">{{ cellParams.alpha.toFixed(2) }}</span>
              <span class="param-unit">°</span>
            </div>
            <div class="param-item">
              <span class="param-label">β</span>
              <span class="param-value">{{ cellParams.beta.toFixed(2) }}</span>
              <span class="param-unit">°</span>
            </div>
            <div class="param-item">
              <span class="param-label">γ</span>
              <span class="param-value">{{ cellParams.gamma.toFixed(2) }}</span>
              <span class="param-unit">°</span>
            </div>
            <div v-if="cellParams.tilt !== undefined" class="param-item tilt-param">
              <span class="param-label">{{ t('results.tiltAngle') }}</span>
              <span class="param-value">{{ cellParams.tilt.toFixed(2) }}</span>
              <span class="param-unit">°</span>
            </div>
            <div v-if="cellParams.volume !== undefined && cellParams.volume !== null" class="param-item volume-param">
      <span class="param-label">{{ t('params.volume') }}</span>
              <span class="param-value">{{ cellParams.volume.toFixed(3) }}</span>
              <span class="param-unit">Å³</span>
            </div>
          </div>
        </div>

        <div class="miller-info-card">
          <h3>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="8" y1="6" x2="21" y2="6"/>
              <line x1="8" y1="12" x2="21" y2="12"/>
              <line x1="8" y1="18" x2="21" y2="18"/>
              <line x1="3" y1="6" x2="3.01" y2="6"/>
              <line x1="3" y1="12" x2="3.01" y2="12"/>
              <line x1="3" y1="18" x2="3.01" y2="18"/>
            </svg>
            {{ t('results.millerIndices') }}
          </h3>
          <div class="miller-stats">
            <div class="stat">
              <span class="stat-value">{{ totalReflections }}</span>
              <span class="stat-label">{{ t('results.totalReflections') }}</span>
            </div>
            <div class="stat">
              <span class="stat-value">{{ indexedPeaks }}</span>
              <span class="stat-label">{{ t('results.indexedPeaks') }}</span>
            </div>
          </div>
          <div class="miller-preview">
            <div class="preview-header" :class="{ 'has-tilt': hasTilt }">
              <span>h</span>
              <span>k</span>
              <span>l</span>
              <span>{{ t('results.qcalc') }}</span>
              <span>{{ t('results.psicalc') }}</span>
              <span v-if="hasTilt">{{ t('results.psiRootCalc') }}</span>
            </div>
            <div class="miller-scroll-container">
              <div v-for="(m, i) in millerData" :key="i" class="preview-row" :class="{ 'has-tilt': hasTilt }">
                <span>{{ m.h }}</span>
                <span>{{ m.k }}</span>
                <span>{{ m.l }}</span>
                <span>{{ m.qcalc.toFixed(3) }}</span>
                <span>{{ m.psicalc.toFixed(2) }}°</span>
                <span v-if="hasTilt && m.psiRootCalc !== null" class="psi-root">
                  {{ m.psiRootCalc.toFixed(2) }}°
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="visualization-section">
        <h3>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
          {{ t('results.structure3D') }}
        </h3>
        <div class="view-controls">
          <button class="view-btn" @click="setView('reset')" :class="{active: currentView === 'reset'}">
            {{ t('results.viewReset') }}
          </button>
          <button class="view-btn" @click="setView('a')" :class="{active: currentView === 'a'}">
            {{ t('results.viewA') }}
          </button>
          <button class="view-btn" @click="setView('b')" :class="{active: currentView === 'b'}">
            {{ t('results.viewB') }}
          </button>
          <button class="view-btn" @click="setView('c')" :class="{active: currentView === 'c'}">
            {{ t('results.viewC') }}
          </button>
        </div>
        <div class="plot-container" ref="plotContainer"></div>
      </div>

      <div class="quality-section">
        <h3>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
            <polyline points="22,4 12,14.01 9,11.01"/>
          </svg>
          {{ t('results.rFactor') }}
        </h3>
        <div class="quality-grid">
          <div class="quality-item">
            <span class="quality-label">{{ t('results.rFactorQ') }}</span>
            <span class="quality-value">{{ rFactorQ.toFixed(4) }}</span>
          </div>
          <div class="quality-item">
            <span class="quality-label">{{ t('results.rFactorPsi') }}</span>
            <span class="quality-value">{{ rFactorPsi.toFixed(4) }}</span>
          </div>
          <div class="quality-item">
            <span class="quality-label">{{ t('results.maxDeviationQ') }}</span>
            <span class="quality-value">{{ maxDeviationQ.toFixed(4) }}</span>
          </div>
          <div class="quality-item">
            <span class="quality-label">{{ t('results.maxDeviationQPoint') }}</span>
            <span class="quality-value">({{ maxDeviationHQ }}, {{ maxDeviationKQ }}, {{ maxDeviationLQ }})</span>
          </div>
          <div class="quality-item">
            <span class="quality-label">{{ t('results.maxDeviationPsi') }}</span>
            <span class="quality-value">{{ maxDeviationPsi.toFixed(4) }}</span>
          </div>
          <div class="quality-item">
            <span class="quality-label">{{ t('results.maxDeviationPsiPoint') }}</span>
            <span class="quality-value">({{ maxDeviationHPsi }}, {{ maxDeviationKPsi }}, {{ maxDeviationLPsi }})</span>
          </div>
        </div>
      </div>

      <div v-if="resultType === 'indexing' && glideBatchOutputs.enabled" class="glide-batch-section">
        <h3>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>
            <line x1="4" y1="22" x2="4" y2="15"/>
          </svg>
          {{ t('results.glideTitle') }}
        </h3>
        <div class="glide-batch-summary">
          <div class="glide-batch-summary-item">
            <span class="summary-label">{{ t('results.groupsLabel') }}</span>
            <span class="summary-value">{{ glideBatchOutputs.groups.length }}</span>
          </div>
          <div class="glide-batch-summary-item">
            <span class="summary-label">{{ t('results.batchRootLabel') }}</span>
            <span class="summary-value">{{ glideBatchOutputs.batchRoot || '—' }}</span>
          </div>
        </div>
        <div v-if="glideBatchOutputs.groups.length" class="glide-batch-list">
          <div v-for="g in glideBatchOutputs.groups" :key="g.label" class="glide-batch-card">
            <div class="glide-batch-card-header">
              <span class="group-badge">{{ g.label }}</span>
              <span class="glide-dir">{{ g.directory }}</span>
            </div>
            <div class="glide-batch-card-meta">
              <span v-if="g.fullMillerFile">{{ t('results.fullMillerLabel') }}: {{ g.fullMillerFile }} ({{ g.fullMillerSize }} B)</span>
              <span v-else>{{ t('results.fullMillerLabel') }}: —</span>
              <span v-if="g.outputMillerFile">{{ t('results.outputMillerLabel') }}: {{ g.outputMillerFile }} ({{ g.outputMillerSize }} B)</span>
              <span v-if="g.cellParams" class="glide-cell">{{ t('results.cellLabel') }}: {{ g.cellParams.a.toFixed(3) }}, {{ g.cellParams.b.toFixed(3) }}, {{ g.cellParams.c.toFixed(3) }}, {{ g.cellParams.alpha.toFixed(2) }}, {{ g.cellParams.beta.toFixed(2) }}, {{ g.cellParams.gamma.toFixed(2) }}</span>
            </div>
          </div>
        </div>
      </div>

      <div v-if="resultType === 'indexing'" class="export-section">
        <h3>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="7,10 12,15 17,10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          {{ t('results.exportResults') }}
        </h3>
        <div class="export-options">
          <button class="export-btn" @click="exportZip">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
              <polyline points="7,10 12,15 17,10"/>
              <line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            <span class="export-label">{{ t('results.downloadPackage') }}</span>
            <span class="export-desc">{{ t('results.packageDesc') }}</span>
          </button>
          <button class="export-btn" @click="exportCell">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
            </svg>
            <span class="export-label">{{ t('results.cellOnly') }}</span>
            <span class="export-desc">{{ t('results.cellDesc') }}</span>
          </button>
          <button class="export-btn" @click="exportMiller">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
            <span class="export-label">{{ t('results.millerOnly') }}</span>
            <span class="export-desc">{{ t('results.millerDesc') }}</span>
          </button>
          <button class="export-btn" @click="exportHDF5">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
              <polyline points="3.27,6.96 12,12.01 20.73,6.96"/>
              <line x1="12" y1="22.08" x2="12" y2="12"/>
            </svg>
            <span class="export-label">{{ t('results.exportHDF5') }}</span>
            <span class="export-desc">{{ t('results.hdf5Desc') }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '@/api/index'

const props = defineProps({
  resultType: {
    type: String,
    default: 'indexing',
    validator: (v) => ['indexing', 'glide', 'manual'].includes(v),
  },
  resultData: {
    type: Object,
    default: null,
  },
})

const { t } = useI18n()
const emit = defineEmits(['navigate'])
const router = useRouter()
const route = useRoute()

const isExternalResult = computed(() => props.resultType !== 'indexing' && props.resultData)

const hasResults = ref(false)
const cellParams = ref({
  a: 5.423,
  b: 6.157,
  c: 7.215,
  alpha: 90.0,
  beta: 95.12,
  gamma: 90.0,
  volume: null
})
const millerData = ref([])
const totalReflections = ref(0)
const indexedPeaks = ref(0)
const hasTilt = computed(() => cellParams.value.tilt !== undefined && cellParams.value.tilt !== null)
const plotContainer = ref(null)
const rFactor = ref(0.0234)
const rFactorQ = ref(0.0)
const rFactorPsi = ref(0.0)
const maxDeviation = ref(0.0892)
const maxDeviationQ = ref(0.0)
const maxDeviationPsi = ref(0.0)
const maxDeviationHQ = ref(1)
const maxDeviationKQ = ref(1)
const maxDeviationLQ = ref(0)
const maxDeviationHPsi = ref(1)
const maxDeviationKPsi = ref(1)
const maxDeviationLPsi = ref(1)
const currentTaskId = ref(null)
const currentView = ref('reset')
const glideBatchOutputs = ref({ enabled: false, groups: [], batchRoot: '' })

const formatMetric = (value, digits) => Number(value ?? 0).toFixed(digits)
const formatPeakIndices = (indices) => Array.isArray(indices) ? indices.join(', ') : ''
const getMillerQ = (m) => Number(m?.qcalc ?? m?.q ?? 0)
const getMillerPsi = (m) => Number(m?.psicalc ?? m?.psi ?? 0)

const startAnalysis = () => {
  emit('navigate', 'console')
  if (route.path === '/app/results') {
    router.push('/app/indexing')
  }
}

const setView = (view) => {
  currentView.value = view
  if (plotContainer.value && typeof window !== 'undefined') {
    import('plotly.js-dist-min').then((Plotly) => {
      const { a, b, c, alpha, beta, gamma } = cellParams.value
      const alphaRad = alpha * Math.PI / 180
      const betaRad = beta * Math.PI / 180
      const gammaRad = gamma * Math.PI / 180

      const va = [a, 0, 0]
      const vb = [b * Math.cos(gammaRad), b * Math.sin(gammaRad), 0]
      const vc = [
        c * Math.cos(betaRad),
        c * (Math.cos(alphaRad) - Math.cos(betaRad) * Math.cos(gammaRad)) / Math.sin(gammaRad),
        Math.sqrt(c * c - (c * Math.cos(betaRad)) ** 2 - (c * (Math.cos(alphaRad) - Math.cos(betaRad) * Math.cos(gammaRad)) / Math.sin(gammaRad)) ** 2)
      ]

      const normA = Math.sqrt(va[0]**2 + va[1]**2 + va[2]**2)
      const normB = Math.sqrt(vb[0]**2 + vb[1]**2 + vb[2]**2)
      const normC = Math.sqrt(vc[0]**2 + vc[1]**2 + vc[2]**2)

      const camA = [va[0]/normA * 2, va[1]/normA * 2, va[2]/normA * 2]
      const camB = [vb[0]/normB * 2, vb[1]/normB * 2, vb[2]/normB * 2]
      const camC = [vc[0]/normC * 2, vc[1]/normC * 2, vc[2]/normC * 2]

      let camera
      if (view === 'a') {
        camera = { eye: { x: camA[0], y: camA[1], z: camA[2] }, up: { x: 0, y: 0, z: 1 } }
      } else if (view === 'b') {
        camera = { eye: { x: camB[0], y: camB[1], z: camB[2] }, up: { x: 0, y: 0, z: 1 } }
      } else if (view === 'c') {
        camera = { eye: { x: camC[0], y: camC[1], z: camC[2] }, up: { x: 0, y: 1, z: 0 } }
      } else {
        camera = { eye: { x: 1.5, y: 1.5, z: 1.5 }, up: { x: 0, y: 0, z: 1 } }
      }

      Plotly.relayout(plotContainer.value, {
        'scene.camera': {
          projection: { type: 'orthographic' },
          ...camera
        }
      })
    })
  }
}

const applyExternalResult = (data) => {
  if (!data) return
  cellParams.value = data.cellParams || cellParams.value
  millerData.value = data.millerData || []
  totalReflections.value = data.totalReflections || 0
  indexedPeaks.value = data.indexedPeaks || millerData.value.length
  currentTaskId.value = data.taskId || null
  if (data.rFactorQ !== undefined) rFactorQ.value = data.rFactorQ
  if (data.rFactorPsi !== undefined) rFactorPsi.value = data.rFactorPsi
  if (data.qualityMetrics) {
    rFactor.value = data.qualityMetrics.r_factor || 0
    rFactorQ.value = data.qualityMetrics.r_factor_q || rFactorQ.value
    rFactorPsi.value = data.qualityMetrics.r_factor_psi || rFactorPsi.value
    maxDeviationQ.value = data.qualityMetrics.max_deviation_q || 0
    maxDeviationPsi.value = data.qualityMetrics.max_deviation_psi || 0
    if (data.qualityMetrics.max_deviation_q_point) {
      maxDeviationHQ.value = data.qualityMetrics.max_deviation_q_point.h || 0
      maxDeviationKQ.value = data.qualityMetrics.max_deviation_q_point.k || 0
      maxDeviationLQ.value = data.qualityMetrics.max_deviation_q_point.l || 0
    }
    if (data.qualityMetrics.max_deviation_psi_point) {
      maxDeviationHPsi.value = data.qualityMetrics.max_deviation_psi_point.h || 0
      maxDeviationKPsi.value = data.qualityMetrics.max_deviation_psi_point.k || 0
      maxDeviationLPsi.value = data.qualityMetrics.max_deviation_psi_point.l || 0
    }
  }
  hasResults.value = true
}

const loadResults = async () => {
  if (isExternalResult.value) {
    applyExternalResult(props.resultData)
    return
  }
  try {
    const result = await api.getResults()
    if (result.success && result.data) {
      cellParams.value = result.data.cellParams || cellParams.value
      millerData.value = result.data.millerData || millerData.value
      totalReflections.value = result.data.totalReflections || 0
      indexedPeaks.value = result.data.indexedPeaks || millerData.value.length
      currentTaskId.value = result.data.taskId || null
      glideBatchOutputs.value = result.data.glideBatchOutputs || glideBatchOutputs.value

      if (result.data.qualityMetrics) {
        rFactor.value = result.data.qualityMetrics.r_factor || 0
        rFactorQ.value = result.data.qualityMetrics.r_factor_q || 0
        rFactorPsi.value = result.data.qualityMetrics.r_factor_psi || 0
        maxDeviationQ.value = result.data.qualityMetrics.max_deviation_q || 0
        maxDeviationPsi.value = result.data.qualityMetrics.max_deviation_psi || 0
        if (result.data.qualityMetrics.max_deviation_q_point) {
          maxDeviationHQ.value = result.data.qualityMetrics.max_deviation_q_point.h || 0
          maxDeviationKQ.value = result.data.qualityMetrics.max_deviation_q_point.k || 0
          maxDeviationLQ.value = result.data.qualityMetrics.max_deviation_q_point.l || 0
        }
        if (result.data.qualityMetrics.max_deviation_psi_point) {
          maxDeviationHPsi.value = result.data.qualityMetrics.max_deviation_psi_point.h || 0
          maxDeviationKPsi.value = result.data.qualityMetrics.max_deviation_psi_point.k || 0
          maxDeviationLPsi.value = result.data.qualityMetrics.max_deviation_psi_point.l || 0
        }
      }
      
      hasResults.value = true
    }
  } catch (error) {
    hasResults.value = false
  }
}

const plot3DCell = () => {
  if (!plotContainer.value || !hasResults.value) return

  const { a, b, c, alpha, beta, gamma } = cellParams.value

  const alphaRad = alpha * Math.PI / 180
  const betaRad = beta * Math.PI / 180
  const gammaRad = gamma * Math.PI / 180

  const va = [a, 0, 0]
  const vb = [b * Math.cos(gammaRad), b * Math.sin(gammaRad), 0]
  const vc = [
    c * Math.cos(betaRad),
    c * (Math.cos(alphaRad) - Math.cos(betaRad) * Math.cos(gammaRad)) / Math.sin(gammaRad),
    Math.sqrt(c * c - (c * Math.cos(betaRad)) ** 2 - (c * (Math.cos(alphaRad) - Math.cos(betaRad) * Math.cos(gammaRad)) / Math.sin(gammaRad)) ** 2)
  ]

  const p0 = [0, 0, 0]
  const p1 = va
  const p2 = vb
  const p3 = vc
  const p4 = va.map((v, i) => v + vb[i])
  const p5 = va.map((v, i) => v + vc[i])
  const p6 = vb.map((v, i) => v + vc[i])
  const p7 = va.map((v, i) => v + vb[i] + vc[i])

  const edges = [
    [p0, p1], [p0, p2], [p0, p3],
    [p1, p4], [p2, p4],
    [p1, p5], [p3, p5],
    [p2, p6], [p3, p6],
    [p4, p7], [p5, p7], [p6, p7]
  ]

  const traces = edges.map(([start, end]) => ({
    type: 'scatter3d',
    mode: 'lines',
    x: [start[0], end[0]],
    y: [start[1], end[1]],
    z: [start[2], end[2]],
    line: { color: '#1E40AF', width: 4 },
    hoverinfo: 'skip'
  }))

  const axisVecs = [
    { vec: va, color: '#EF4444', label: 'a' },
    { vec: vb, color: '#10B981', label: 'b' },
    { vec: vc, color: '#3B82F6', label: 'c' }
  ]

  axisVecs.forEach(({ vec, color, label }) => {
    traces.push({
      type: 'scatter3d',
      mode: 'lines+text',
      x: [0, vec[0]],
      y: [0, vec[1]],
      z: [0, vec[2]],
      line: { color, width: 6 },
      text: ['', label],
      textposition: 'top center',
      textfont: { size: 14, color },
      hoverinfo: 'text'
    })
  })

  const layout = {
    scene: {
      xaxis: { title: 'X (Å)', showbackground: false, showgrid: false, zeroline: false },
      yaxis: { title: 'Y (Å)', showbackground: false, showgrid: false, zeroline: false },
      zaxis: { title: 'Z (Å)', showbackground: false, showgrid: false, zeroline: false },
      aspectmode: 'data',
      camera: { projection: { type: 'orthographic' }, eye: { x: 1.5, y: 1.5, z: 1.5 } }
    },
    margin: { l: 0, r: 0, b: 0, t: 30 },
    height: 450,
    paper_bgcolor: 'white',
    showlegend: false
  }

  if (typeof window !== 'undefined' && plotContainer.value) {
    import('plotly.js-dist-min').then((Plotly) => {
      Plotly.newPlot(plotContainer.value, traces, layout, { displayModeBar: true })
    })
  }
}

const exportZip = async () => {
  try {
    const { blob, filename } = await api.downloadResults('zip', currentTaskId.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    alert(t('results.downloadPackage') + ' failed: ' + error.message)
  }
}

const exportCell = async () => {
  try {
    const { blob, filename } = await api.downloadResults('cell', currentTaskId.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    const content = `${cellParams.value.a} ${cellParams.value.b} ${cellParams.value.c} ${cellParams.value.alpha} ${cellParams.value.beta} ${cellParams.value.gamma}`
    downloadFile(content, 'cell_parameters.txt', 'text/plain')
  }
}

const exportMiller = async () => {
  try {
    const { blob, filename } = await api.downloadResults('miller', currentTaskId.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    let content = 'h    k    l    q        psi\n'
    millerData.value.forEach(m => {
      content += `${m.h}   ${m.k}   ${m.l}   ${getMillerQ(m).toFixed(4)}   ${getMillerPsi(m).toFixed(2)}\n`
    })
    downloadFile(content, 'miller_indices.txt', 'text/plain')
  }
}

const exportHDF5 = async () => {
  try {
    const { blob, filename } = await api.downloadResults('hdf5', currentTaskId.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  } catch (error) {
    const hdf5Data = {
      version: '1.8.2',
      timestamp: new Date().toISOString(),
      cellParameters: cellParams.value,
      millerIndices: millerData.value,
      qualityMetrics: {
        rFactor: rFactor.value,
        maxDeviation: maxDeviation.value,
        maxDeviationQPoint: {
          h: maxDeviationHQ.value,
          k: maxDeviationKQ.value,
          l: maxDeviationLQ.value,
          q: maxDeviationQ.value
        },
        maxDeviationPsiPoint: {
          h: maxDeviationHPsi.value,
          k: maxDeviationKPsi.value,
          l: maxDeviationLPsi.value,
          psi: maxDeviationPsi.value
        }
      },
      metadata: {
        program: 'PolymCrystIndex',
        dataPoints: millerData.value.length
      }
    }
    const content = JSON.stringify(hdf5Data, null, 2)
    downloadFile(content, 'polymcryst_results_fallback.json', 'application/json')
  }
}

const downloadFile = (content, filename, type) => {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  await loadResults()
  await nextTick()
  plot3DCell()
})

watch(() => props.resultData, async (newData) => {
  if (newData && isExternalResult.value) {
    applyExternalResult(newData)
    await nextTick()
    plot3DCell()
  }
})
</script>

<style scoped>
.result-export {
  max-width: 1100px;
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

.no-results {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 40px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  text-align: center;
}

.no-results-icon {
  width: 80px;
  height: 80px;
  color: var(--text-muted);
  margin-bottom: 24px;
}

.no-results-icon svg {
  width: 100%;
  height: 100%;
}

.no-results h3 {
  font-size: 1.25rem;
  margin-bottom: 8px;
}

.no-results p {
  color: var(--text-secondary);
  margin-bottom: 24px;
}

.btn-start {
  display: flex;
  align-items: center;
  gap: 10px;
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

.btn-start:hover {
  background: var(--primary-dark);
  transform: translateY(-1px);
}

.btn-start svg {
  width: 18px;
  height: 18px;
}

.results-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.success-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid var(--secondary);
  border-radius: var(--radius-lg);
  color: var(--secondary);
  font-weight: 600;
}

.success-banner svg {
  width: 24px;
  height: 24px;
}

.results-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.cell-params-card,
.miller-info-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.cell-params-card h3,
.miller-info-card h3,
.peak-symmetry-section h3,
.visualization-section h3,
.export-section h3 {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 1rem;
  margin-bottom: 16px;
  color: var(--text-primary);
}

.cell-params-card h3 svg,
.miller-info-card h3 svg,
.peak-symmetry-section h3 svg,
.visualization-section h3 svg,
.export-section h3 svg {
  width: 20px;
  height: 20px;
  color: var(--primary);
}

.peak-symmetry-section {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.peak-symmetry-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.peak-symmetry-summary.disabled {
  opacity: 0.75;
}

.peak-symmetry-summary-item,
.peak-symmetry-group-card {
  background: var(--bg-surface-alt);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
}

.summary-label {
  display: block;
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: 6px;
}

.summary-value {
  font-weight: 600;
  color: var(--text-primary);
}

.peak-symmetry-list {
  display: grid;
  gap: 12px;
}

.peak-symmetry-group-header,
.peak-symmetry-group-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.peak-symmetry-group-header {
  margin-bottom: 8px;
}

.group-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--primary-bg);
  color: var(--primary);
  font-size: 0.75rem;
  font-weight: 700;
}

.group-members,
.peak-symmetry-group-meta,
.peak-symmetry-empty {
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.glide-batch-section {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.glide-batch-section h3 {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 1rem;
  margin-bottom: 16px;
  color: var(--text-primary);
}

.glide-batch-section h3 svg {
  width: 20px;
  height: 20px;
  color: var(--primary);
}

.glide-batch-summary {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.glide-batch-summary-item {
  background: var(--bg-surface-alt);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
}

.glide-batch-list {
  display: grid;
  gap: 12px;
}

.glide-batch-card {
  background: var(--bg-surface-alt);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
}

.glide-batch-card-header {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  margin-bottom: 8px;
}

.glide-dir {
  font-family: 'Fira Code', monospace;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.glide-batch-card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  color: var(--text-secondary);
  font-size: 0.8125rem;
}

.glide-cell {
  font-family: 'Fira Code', monospace;
}

.params-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.param-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-md);
}

.param-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.param-value {
  font-size: 1.25rem;
  font-weight: 700;
  font-family: 'Fira Code', monospace;
  color: var(--primary);
}

.param-unit {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.tilt-param {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid var(--secondary);
}

.tilt-param .param-value {
  color: var(--secondary);
}

.miller-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
}

.stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 700;
  font-family: 'Fira Code', monospace;
  color: var(--primary);
}

.stat-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.miller-preview {
  background: var(--bg-surface-alt);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.miller-scroll-container {
  max-height: 300px;
  overflow-y: auto;
}

.miller-scroll-container::-webkit-scrollbar {
  width: 6px;
}

.miller-scroll-container::-webkit-scrollbar-track {
  background: var(--bg-surface-alt);
}

.miller-scroll-container::-webkit-scrollbar-thumb {
  background: var(--border);
  border-radius: 3px;
}

.miller-scroll-container::-webkit-scrollbar-thumb:hover {
  background: var(--border-hover);
}

.preview-header {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  padding: 8px 12px;
  background: var(--border);
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
  text-align: center;
}

.preview-header.has-tilt {
  grid-template-columns: repeat(6, 1fr);
}

.preview-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  padding: 8px 12px;
  font-size: 0.8125rem;
  font-family: 'Fira Code', monospace;
  text-align: center;
  border-bottom: 1px solid var(--border);
}

.preview-row.has-tilt {
  grid-template-columns: repeat(6, 1fr);
}

.psi-root {
  color: var(--secondary);
  font-weight: 600;
}

.preview-row:last-child {
  border-bottom: none;
}

.preview-more {
  padding: 8px 12px;
  font-size: 0.75rem;
  color: var(--text-muted);
  text-align: center;
}

.visualization-section {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.view-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.view-btn {
  padding: 6px 16px;
  background: var(--bg-surface-alt);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-primary);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.view-btn:hover {
  background: var(--bg-hover);
  border-color: var(--primary-light);
}

.view-btn.active {
  background: var(--primary-bg);
  border-color: var(--primary);
  color: var(--primary);
}

.plot-container {
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.export-section {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.quality-section {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.quality-section h3 {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 1rem;
  margin-bottom: 16px;
  color: var(--text-primary);
}

.quality-section h3 svg {
  width: 20px;
  height: 20px;
  color: var(--primary);
}

.quality-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.quality-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-md);
}

.quality-label {
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.quality-value {
  font-size: 1.125rem;
  font-weight: 700;
  font-family: 'Fira Code', monospace;
  color: var(--primary);
}

.export-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.export-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  background: var(--bg-surface-alt);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-normal);
  text-align: center;
}

.export-btn:hover {
  background: var(--bg-hover);
  border-color: var(--primary-light);
  transform: translateY(-2px);
}

.export-btn svg {
  width: 32px;
  height: 32px;
  color: var(--primary);
}

.export-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--text-primary);
}

.export-desc {
  font-size: 0.75rem;
  color: var(--text-muted);
}

@media (max-width: 768px) {
  .results-grid {
    grid-template-columns: 1fr;
  }

  .export-options {
    grid-template-columns: 1fr;
  }
}
</style>
