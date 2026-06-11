<template>
  <div class="manual-cell-panel">
    <div class="page-header">
      <h2>{{ panelTitle }}</h2>
      <p>{{ panelSubtitle }}</p>
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

        <div v-if="reciprocalCell(group)" class="reciprocal-section">
          <div class="reciprocal-header">
            <span class="reciprocal-title">{{ t('manual.reciprocalCell') }}</span>
            <span class="reciprocal-hint">{{ t('manual.reciprocalCellHint') }}</span>
          </div>
          <div class="reciprocal-values">
            <span class="reciprocal-item">a* = {{ reciprocalCell(group).a.toFixed(4) }} Å⁻¹</span>
            <span class="reciprocal-item">b* = {{ reciprocalCell(group).b.toFixed(4) }} Å⁻¹</span>
            <span class="reciprocal-item">c* = {{ reciprocalCell(group).c.toFixed(4) }} Å⁻¹</span>
            <span class="reciprocal-item">α* = {{ reciprocalCell(group).alpha.toFixed(2) }}°</span>
            <span class="reciprocal-item">β* = {{ reciprocalCell(group).beta.toFixed(2) }}°</span>
            <span class="reciprocal-item">γ* = {{ reciprocalCell(group).gamma.toFixed(2) }}°</span>
          </div>
          <div class="reciprocal-projection">
            <span class="reciprocal-projection-label">{{ t('manual.projection') }}</span>
            <span class="reciprocal-item"><span v-html="t('manual.aProjection')"></span> = {{ reciprocalCell(group).a > 1e-12 ? (1 / reciprocalCell(group).a).toFixed(4) : '∞' }} Å</span>
            <span class="reciprocal-item"><span v-html="t('manual.bProjection')"></span> = {{ reciprocalCell(group).b > 1e-12 ? (1 / reciprocalCell(group).b).toFixed(4) : '∞' }} Å</span>
          </div>
        </div>

        <div v-if="reciprocalCell(group) && !isSupercellMode" class="equivalent-cell-section">
          <button class="eq-toggle" @click="toggleEqCell(idx)">
            <svg class="chevron-icon" :class="{ expanded: eqCellExpanded[idx] }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6,9 12,15 18,9"/>
            </svg>
            <span class="eq-toggle-text">{{ t('manual.equivalentCellTitle') }}</span>
          </button>

          <div v-if="eqCellExpanded[idx]" class="eq-content">
            <p class="eq-hint">{{ t('manual.equivalentCellHint') }}</p>

            <div class="eq-constraints">
              <div class="eq-row">
                <span class="eq-row-label">{{ t('manual.eqConstraint1') }}</span>
                <span class="eq-label-tag">{{ t('manual.eqOld') }}</span>
                <input type="number" v-model.number="eqData[idx].h1" class="eq-input" />
                <input type="number" v-model.number="eqData[idx].k1" class="eq-input" />
                <span class="eq-arrow">{{ t('manual.eqArrow') }}</span>
                <span class="eq-label-tag">{{ t('manual.eqNew') }}</span>
                <input type="number" v-model.number="eqData[idx].h1p" class="eq-input" />
                <input type="number" v-model.number="eqData[idx].k1p" class="eq-input" />
              </div>
              <div class="eq-row">
                <span class="eq-row-label">{{ t('manual.eqConstraint2') }}</span>
                <span class="eq-label-tag">{{ t('manual.eqOld') }}</span>
                <input type="number" v-model.number="eqData[idx].h2" class="eq-input" />
                <input type="number" v-model.number="eqData[idx].k2" class="eq-input" />
                <span class="eq-arrow">{{ t('manual.eqArrow') }}</span>
                <span class="eq-label-tag">{{ t('manual.eqNew') }}</span>
                <input type="number" v-model.number="eqData[idx].h2p" class="eq-input" />
                <input type="number" v-model.number="eqData[idx].k2p" class="eq-input" />
              </div>
              <p class="eq-default-hint">{{ t('manual.eqDefaultHint') }}</p>
            </div>

            <div v-if="equivalentCellError(idx)" class="eq-error">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>
              </svg>
              <span>{{ equivalentCellError(idx) }}</span>
            </div>

            <div v-if="equivalentCellResult(group, idx)" class="eq-result">
              <div class="eq-result-header">
                <span class="eq-result-title">{{ t('manual.eqResultTitle') }}</span>
              </div>
              <div class="eq-result-values">
                <span class="eq-result-item">a*<sub>eq</sub> = {{ equivalentCellResult(group, idx).a.toFixed(4) }} Å⁻¹</span>
                <span class="eq-result-item">b*<sub>eq</sub> = {{ equivalentCellResult(group, idx).b.toFixed(4) }} Å⁻¹</span>
                <span class="eq-result-item">γ*<sub>eq</sub> = {{ equivalentCellResult(group, idx).gamma.toFixed(2) }}°</span>
              </div>
              <div class="eq-result-projection">
                <span class="eq-result-item">a<sub>投影</sub> = {{ equivalentCellResult(group, idx).aProj.toFixed(4) }} Å</span>
                <span class="eq-result-item">b<sub>投影</sub> = {{ equivalentCellResult(group, idx).bProj.toFixed(4) }} Å</span>
                <span class="eq-result-item">{{ t('manual.eqAreaRatio') }}: {{ equivalentCellResult(group, idx).areaRatio.toFixed(4) }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="isSupercellMode" class="supercell-section">
          <h3>{{ t('manual.supercellFactors') }}</h3>
          <p class="supercell-hint">{{ t('manual.supercellFactorTip') }}</p>
          <div class="cell-inputs supercell-inputs">
            <div class="input-group">
              <label>{{ t('manual.na') }}</label>
              <input type="number" v-model.number="group.na" step="1" min="1" @change="enforcePositiveInt(group, 'na')" />
            </div>
            <div class="input-group">
              <label>{{ t('manual.nb') }}</label>
              <input type="number" v-model.number="group.nb" step="1" min="1" @change="enforcePositiveInt(group, 'nb')" />
            </div>
            <div class="input-group">
              <label>{{ t('manual.nc') }}</label>
              <input type="number" v-model.number="group.nc" step="1" min="1" @change="enforcePositiveInt(group, 'nc')" />
            </div>
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
          {{ generating ? t('manual.generating') : generateButtonText }}
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

          <div v-if="res.data?.supercellFactors" class="cell-info supercell-info-row">
            <span class="cell-label">{{ t('manual.supercellTab') }}</span>
            <span class="cell-value">
              {{ t('manual.supercellInfo', {
                na: res.data.supercellFactors.na,
                nb: res.data.supercellFactors.nb,
                nc: res.data.supercellFactors.nc,
                total: res.data.supercellFactors.total
              }) }}
            </span>
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

      <div v-if="browsableResults.length" class="quick-browse-section">
        <button class="quick-browse-toggle" @click="toggleBrowseExpanded">
          <svg class="chevron-icon" :class="{ expanded: browseExpanded }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="6,9 12,15 18,9"/>
          </svg>
          {{ browseExpanded ? t('manual.quickBrowseCollapse') : t('manual.quickBrowseExpand') }}
        </button>

        <div v-if="browseExpanded" class="quick-browse-content">
          <div class="browse-mode-switch">
            <label class="mode-option">
              <input v-model="browseMode" type="radio" value="single" />
              <span>{{ t('manual.browseModeSingle') }}</span>
            </label>
            <label class="mode-option">
              <input v-model="browseMode" type="radio" value="overlay" />
              <span>{{ t('manual.browseModeOverlay') }}</span>
            </label>
          </div>

          <div v-if="browseMode === 'single'" class="selection-panel">
            <label class="selection-label">{{ t('manual.selectGroup') }}</label>
            <select v-model="selectedSingleLabel" class="group-select">
              <option v-for="group in browsableResults" :key="group.label" :value="group.label">
                {{ group.label }} · {{ group.totalReflections || 0 }}
              </option>
            </select>
          </div>

          <div v-else class="selection-panel">
            <label class="selection-label">{{ t('manual.overlaySelectionTitle') }}</label>
            <p class="quick-browse-hint">{{ t('manual.overlayHint') }}</p>
            <div class="overlay-checklist">
              <label v-for="group in browsableResults" :key="group.label" class="overlay-item" :class="{ active: selectedOverlayLabels.includes(group.label) }">
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
            <span class="overlay-limit">{{ t('manual.selectedCount', { count: selectedGroups.length }) }}</span>
            <span v-if="selectedOverlayLabels.length >= 5" class="overlay-limit warning">{{ t('manual.overlayLimit') }}</span>
          </div>

          <p class="quick-browse-hint">{{ t('manual.liveSyncHint') }}</p>

          <div v-if="selectedGroups.length > 0" class="shared-visualizer">
            <Visualizer
              resultType="manual"
              :overlayGroups="selectedGroups"
              :importRequestKey="importSelectionKey"
              @raw-session-ready="handleVisualizerReady"
              compact
            />
          </div>
          <p v-else class="quick-browse-empty">{{ t('manual.selectGroup') }}</p>
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

const props = defineProps({
  mode: {
    type: String,
    default: 'cell'
  }
})

const { t } = useI18n()
const isSupercellMode = computed(() => props.mode === 'supercell')

const panelTitle = computed(() => (isSupercellMode.value ? t('manual.supercellTitle') : t('manual.title')))
const panelSubtitle = computed(() => (isSupercellMode.value ? t('manual.supercellSubtitle') : t('manual.subtitle')))

const defaultGroup = () => ({
  a: 7.40, b: 4.93, c: 2.54,
  alpha: 90.0, beta: 90.0, gamma: 90.0,
  wavelength: 1.542,
  na: 1, nb: 1, nc: 1,
})

const groups = reactive([defaultGroup()])
const generating = ref(false)
const error = ref(null)
const batchResults = ref([])
const browseExpanded = ref(false)
const keepBrowseExpanded = ref(false)
const browseMode = ref('single')
const selectedSingleLabel = ref('')
const selectedOverlayLabels = ref([])
const importSelectionKey = ref(0)
const visualizerReady = ref(false)

/* --- Equivalent Cell Explorer state --- */
const defaultEqData = () => ({
  h1: 1, k1: 0, h1p: 1, k1p: 1,
  h2: 0, k2: 1, h2p: 0, k2p: 1,
})
const eqData = reactive([defaultEqData()])
const eqCellExpanded = ref([])

const toggleEqCell = (idx) => {
  if (!eqCellExpanded.value[idx]) {
    eqCellExpanded.value[idx] = true
  } else {
    eqCellExpanded.value[idx] = false
  }
}

const equivalentCellResult = (group, idx) => {
  const rc = reciprocalCell(group)
  if (!rc) return null
  const d = eqData[idx]
  if (!d) return null

  const toRad = Math.PI / 180
  const gstar = rc.gamma * toRad

  // Old basis vectors in 2D Cartesian (a* along x-axis)
  const ax = rc.a, ay = 0
  const bx = rc.b * Math.cos(gstar), by = rc.b * Math.sin(gstar)

  // Physical vectors for the two constraints
  const v1x = d.h1 * ax + d.k1 * bx
  const v1y = d.h1 * ay + d.k1 * by
  const v2x = d.h2 * ax + d.k2 * bx
  const v2y = d.h2 * ay + d.k2 * by

  // M_new = [[h1p, k1p], [h2p, k2p]]
  const det = d.h1p * d.k2p - d.k1p * d.h2p
  if (Math.abs(det) < 1e-12) return null

  // M_new^{-1}
  const inv00 = d.k2p / det, inv01 = -d.k1p / det
  const inv10 = -d.h2p / det, inv11 = d.h1p / det

  // New basis vectors
  const axNew = inv00 * v1x + inv01 * v2x
  const ayNew = inv00 * v1y + inv01 * v2y
  const bxNew = inv10 * v1x + inv11 * v2x
  const byNew = inv10 * v1y + inv11 * v2y

  const astarNew = Math.sqrt(axNew * axNew + ayNew * ayNew)
  const bstarNew = Math.sqrt(bxNew * bxNew + byNew * byNew)

  if (astarNew < 1e-12 || bstarNew < 1e-12) return null

  const clamp = (v) => Math.max(-1, Math.min(1, v))
  const cosGammaNew = clamp((axNew * bxNew + ayNew * byNew) / (astarNew * bstarNew))
  const gammaNew = Math.acos(cosGammaNew) / toRad

  // Area ratio (determinant of transformation)
  const detOld = d.h1 * d.k2 - d.k1 * d.h2
  const areaRatio = Math.abs(detOld / det)

  return {
    a: astarNew,
    b: bstarNew,
    gamma: gammaNew,
    aProj: 1 / astarNew,
    bProj: 1 / bstarNew,
    areaRatio,
  }
}

const equivalentCellError = (idx) => {
  const d = eqData[idx]
  if (!d) return null
  const det = d.h1p * d.k2p - d.k1p * d.h2p
  if (Math.abs(det) < 1e-12) return t('manual.eqErrorSingular')
  // Try computing — check for invalid result
  const group = groups[idx]
  const rc = reciprocalCell(group)
  if (!rc) return null
  const result = equivalentCellResult(group, idx)
  if (!result) return t('manual.eqErrorInvalid')
  return null
}

const supercellTotal = computed(() => {
  if (!isSupercellMode.value) return 0
  return groups.reduce((sum, g) => sum + (g.na || 1) * (g.nb || 1) * (g.nc || 1), 0)
})

const generateButtonText = computed(() => {
  if (isSupercellMode.value) {
    return t('manual.supercellGenerate', { count: supercellTotal.value })
  }
  return t('manual.generate', { count: groups.length, plural: groups.length > 1 ? 's' : '' })
})

const browsableResults = computed(() => {
  return batchResults.value
    .filter(r => r.success && (r.data?.workDir || r.data?.fullMillerContent))
    .map(r => ({
      label: r.label || r.data?.label || '',
      fullMillerContent: r.data?.fullMillerContent || '',
      outputMillerContent: r.data?.outputMillerContent || '',
      workDir: r.data?.workDir || '',
      totalReflections: r.data?.totalReflections || 0,
    }))
})

const selectedGroups = computed(() => {
  if (browseMode.value === 'overlay') {
    return browsableResults.value.filter(group => selectedOverlayLabels.value.includes(group.label)).slice(0, 5)
  }
  return browsableResults.value.filter(group => group.label === selectedSingleLabel.value).slice(0, 1)
})

const reciprocalCell = (group) => {
  const toRad = Math.PI / 180
  const a = group.a, b = group.b, c = group.c
  const alpha = group.alpha * toRad, beta = group.beta * toRad, gamma = group.gamma * toRad
  const ca = Math.cos(alpha), cb = Math.cos(beta), cg = Math.cos(gamma)
  const sa = Math.sin(alpha), sb = Math.sin(beta), sg = Math.sin(gamma)
  const V = a * b * c * Math.sqrt(1 - ca * ca - cb * cb - cg * cg + 2 * ca * cb * cg)
  if (V < 1e-12) return null
  const astar = b * c * sa / V
  const bstar = a * c * sb / V
  const cstar = a * b * sg / V
  const cosAlphaStar = (cb * cg - ca) / (sb * sg)
  const cosBetaStar = (ca * cg - cb) / (sa * sg)
  const cosGammaStar = (ca * cb - cg) / (sa * sb)
  const clamp = (v) => Math.max(-1, Math.min(1, v))
  return {
    a: astar, b: bstar, c: cstar,
    alpha: Math.acos(clamp(cosAlphaStar)) / toRad,
    beta: Math.acos(clamp(cosBetaStar)) / toRad,
    gamma: Math.acos(clamp(cosGammaStar)) / toRad,
  }
}

const enforcePositiveInt = (group, field) => {
  const val = group[field]
  if (val == null || Number.isNaN(val) || val < 1) {
    group[field] = 1
  } else {
    group[field] = Math.round(val)
  }
}

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
  () => browsableResults.value.length,
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

watch(() => props.mode, () => {
  error.value = null
})

const addGroup = () => {
  groups.push(defaultGroup())
  eqData.push(defaultEqData())
}

const removeGroup = (idx) => {
  groups.splice(idx, 1)
  eqData.splice(idx, 1)
}

const generate = async () => {
  error.value = null
  generating.value = true

  try {
    if (isSupercellMode.value) {
      const payload = groups.map((g, idx) => ({
        label: `supercell_${String(idx + 1).padStart(2, '0')}`,
        a: g.a, b: g.b, c: g.c,
        alpha: g.alpha, beta: g.beta, gamma: g.gamma,
        wavelength: g.wavelength,
        na: Math.max(1, Math.round(g.na || 1)),
        nb: Math.max(1, Math.round(g.nb || 1)),
        nc: Math.max(1, Math.round(g.nc || 1)),
      }))

      const res = await api.supercellBatchFullmiller(payload)
      if (Array.isArray(res.data) && res.data.length > 0) {
        batchResults.value = res.data.map((item, i) => ({
          ...item,
          label: item.label || item.data?.label || payload[i]?.label || `${t('manual.group', { index: i + 1 })}`,
        }))
        const firstGroup = batchResults.value.find(item => item.success && (item.data?.workDir || item.data?.fullMillerContent))
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
        if (!res.success) {
          error.value = res.message || t('manual.someGroupsFailed')
        }
      } else {
        error.value = res.message || t('manual.generationFailed')
      }
    } else {
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
        const firstGroup = batchResults.value.find(item => item.success && (item.data?.workDir || item.data?.fullMillerContent))
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
        if (!res.success) {
          error.value = res.message || t('manual.someGroupsFailed')
        }
      } else {
        error.value = res.message || t('manual.generationFailed')
      }
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

.supercell-inputs {
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
}

.reciprocal-section {
  margin-top: 12px;
  padding: 12px 16px;
  background: var(--bg-surface-alt);
  border: 1px dashed var(--border);
  border-radius: var(--radius-md);
}

.reciprocal-header {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 8px;
}

.reciprocal-title {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--primary);
}

.reciprocal-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.reciprocal-values {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 6px 16px;
}

.reciprocal-item {
  font-family: 'Fira Code', monospace;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.reciprocal-projection {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dotted var(--border);
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.reciprocal-projection-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--primary);
  white-space: nowrap;
}

.supercell-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed var(--border);
}

.supercell-section h3 {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.supercell-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin: 0 0 12px;
}

.supercell-info-row {
  background: var(--bg-surface-alt);
  padding: 8px 12px;
  border-radius: var(--radius-md);
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

.quick-browse-section {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
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

/* --- Equivalent Cell Explorer --- */
.equivalent-cell-section {
  margin-top: 8px;
  border: 1px dashed var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.eq-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 14px;
  background: var(--bg-surface-alt);
  border: none;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--primary);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.eq-toggle:hover {
  background: var(--bg-hover);
}

.eq-toggle .chevron-icon {
  width: 14px;
  height: 14px;
  color: var(--text-muted);
  transition: transform var(--transition-normal);
}

.eq-toggle .chevron-icon.expanded {
  transform: rotate(180deg);
}

.eq-toggle-text {
  font-size: 0.8125rem;
}

.eq-content {
  padding: 12px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--bg-surface);
}

.eq-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin: 0;
}

.eq-constraints {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.eq-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.eq-row-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--text-secondary);
  min-width: 48px;
}

.eq-label-tag {
  font-size: 0.6875rem;
  font-weight: 500;
  color: var(--text-muted);
  padding: 2px 6px;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-sm);
}

.eq-input {
  width: 52px;
  padding: 5px 6px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  font-family: 'Fira Code', monospace;
  background: var(--bg-surface);
  color: var(--text-primary);
  text-align: center;
  transition: border-color var(--transition-fast);
}

.eq-input:focus {
  outline: none;
  border-color: var(--primary);
}

.eq-arrow {
  font-size: 0.9375rem;
  color: var(--text-muted);
  margin: 0 2px;
}

.eq-default-hint {
  font-size: 0.6875rem;
  color: var(--text-muted);
  margin: 0;
  font-style: italic;
}

.eq-error {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.75rem;
  color: var(--status-error);
  padding: 6px 10px;
  background: rgba(239, 68, 68, 0.06);
  border-radius: var(--radius-sm);
}

.eq-error svg {
  flex-shrink: 0;
}

.eq-result {
  padding: 10px 12px;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.eq-result-header {
  margin-bottom: 2px;
}

.eq-result-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--primary);
}

.eq-result-values {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.eq-result-projection {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
  padding-top: 6px;
  border-top: 1px dotted var(--border);
}

.eq-result-item {
  font-family: 'Fira Code', monospace;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}
</style>
