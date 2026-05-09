<template>
  <div class="int-view">
    <div class="content-grid">
      <div class="section-card heatmap-section">
        <div class="section-header">
          <h3>{{ t('visualizer.integration2D') }}</h3>
        </div>
        <div ref="heatmapDiv" class="heatmap-container"></div>
      </div>

      <div class="left-panel">

        <div class="section-card">
          <div class="section-header">
            <h3>{{ t('visualizer.coordinateRange') }}</h3>
          </div>
          <div class="form-grid-2">
            <div class="form-row"><label>{{ t('peakExtraction.qMin') }}</label><input type="number" v-model.number="qMin" step="0.01" /></div>
            <div class="form-row"><label>{{ t('peakExtraction.qMax') }}</label><input type="number" v-model.number="qMax" step="0.01" /></div>
            <div class="form-row"><label>{{ t('peakExtraction.azMin') }}</label><input type="number" v-model.number="azMin" step="1" /></div>
            <div class="form-row"><label>{{ t('peakExtraction.azMax') }}</label><input type="number" v-model.number="azMax" step="1" /></div>
          </div>
          <div class="btn-row">
            <button class="btn-primary" @click="applyRanges">{{ t('peakExtraction.applyRanges') }}</button>
            <button class="btn-primary" @click="restoreView">{{ t('visualizer.resetView') }}</button>
          </div>
        </div>

        <div class="section-card">
          <div class="section-header">
            <h3>{{ t('visualizer.contrastAndColor') }}</h3>
          </div>
          <div class="form-group">
            <div class="form-row">
              <label>{{ t('peakExtraction.contrastMin') }}</label>
              <input type="range" :min="sliderMin" :max="sliderMax" v-model.number="contrastMin" @input="refreshHeatmap" />
              <span class="value-badge">{{ contrastMin }}</span>
            </div>
            <div class="form-row">
              <label>{{ t('peakExtraction.contrastMax') }}</label>
              <input type="range" :min="sliderMin" :max="sliderMax" v-model.number="contrastMax" @input="refreshHeatmap" />
              <span class="value-badge">{{ contrastMax }}</span>
            </div>
            <div class="form-row compact">
              <label>{{ t('peakExtraction.colormap') }}</label>
              <select v-model="colormap" @change="refreshHeatmap" class="select-small">
                <option v-for="c in colormaps" :key="c.value" :value="c.value">{{ c.label }}</option>
              </select>
            </div>
            </div>
          </div>

          <div class="section-card">
            <div class="section-header">
              <h3>{{ t('peakExtraction.azimuthCrop') }}</h3>
            </div>
            <div class="form-row">
              <label>{{ t('peakExtraction.enableCrop') }}</label>
              <input type="checkbox" v-model="cropP.az_crop_enabled" />
            </div>
            <div class="form-row">
              <label>{{ t('peakExtraction.psiConvention') }}</label>
              <select v-model="cropP.convention" class="select-small">
                <option value="ccw">{{ t('peakExtraction.psiConventionCCW') }}</option>
                <option value="cw">{{ t('peakExtraction.psiConventionCW') }}</option>
              </select>
            </div>
            <div class="form-row">
              <label>{{ t('peakExtraction.psi0CorrespondingAz') }}</label>
              <input type="number" v-model.number="cropP.psi_offset" step="1" />
            </div>
            <div class="form-row">
              <label>{{ t('peakExtraction.fromRelative') }} (°)</label>
              <input type="number" v-model.number="cropP.az_crop_min" step="5" />
            </div>
            <div class="form-row">
              <label>{{ t('peakExtraction.toRelative') }} (°)</label>
              <input type="number" v-model.number="cropP.az_crop_max" step="5" />
            </div>
          </div>

          <div class="section-card">
            <div class="section-header">
              <h3>{{ t('peakExtraction.sliceParams') }}</h3>
            </div>
            <div class="form-grid-2">
              <div class="form-row"><label>{{ t('peakExtraction.azWidth') }}</label><input type="number" v-model.number="sp.az_int_w" step="0.5" @change="fetchSlices" /></div>
              <div class="form-row"><label>{{ t('peakExtraction.qDisplay') }}</label><input type="number" v-model.number="sp.q_disp_r" step="0.05" @change="fetchSlices" /></div>
              <div class="form-row"><label>{{ t('peakExtraction.qWidth') }}</label><input type="number" v-model.number="sp.q_int_w" step="0.005" @change="fetchSlices" /></div>
              <div class="form-row"><label>{{ t('peakExtraction.azDisplay') }}</label><input type="number" v-model.number="sp.az_disp_r" step="5" @change="fetchSlices" /></div>
            </div>
          </div>
        </div>

        <div class="right-panel">
          <div class="tab-bar">
            <button :class="['tab-btn', { active: rtab === 'analysis' }]" @click="rtab = 'analysis'">{{ t('nav.analysis') }}</button>
            <button :class="['tab-btn', { active: rtab === 'records' }]" @click="rtab = 'records'">{{ t('peakExtraction.recordedPoints') }}</button>
          </div>

          <div v-show="rtab === 'analysis'" class="tab-content">
            <div class="section-card">
              <div class="section-header">
                <h3>{{ t('peakExtraction.importFile') }}</h3>
              </div>
              <div class="btn-group">
                <label class="btn-secondary">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                    <polyline points="17,8 12,3 7,8"/>
                    <line x1="12" y1="3" x2="12" y2="15"/>
                  </svg>
                  {{ t('peakExtraction.loadImage') }}
                  <input type="file" accept=".npy,.tiff,.tif" @change="onLoadFile" hidden />
                </label>
                <label class="btn-secondary">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                    <polyline points="14,2 14,8 20,8"/>
                  </svg>
                  {{ t('peakExtraction.importInfo') }}
                  <input type="file" accept=".txt" @change="onImportInfo" hidden />
                </label>
              </div>
              <div class="hint-text">{{ t('peakExtraction.importInfoHint') }}</div>
            </div>

            <div class="section-card">
              <div class="section-header">
                <h3>{{ t('peakExtraction.selectionMode') }}</h3>
              </div>
              <div class="btn-group">
                <button :class="['btn-toggle', { active: mode === 'precise' }]" @click="setMode('precise')">{{ t('peakExtraction.preciseMode') }}</button>
                <button :class="['btn-toggle', { active: mode === 'rough' }]" @click="setMode('rough')">{{ t('peakExtraction.roughMode') }}</button>
              </div>
              <div v-if="sliceCenter" class="slice-info">
                {{ t('peakExtraction.sliceCenter') }}: q={{ sliceCenter.q.toFixed(4) }}, Az={{ sliceCenter.az.toFixed(2) }}°
              </div>
            </div>

            <div v-if="sessionId" class="section-card">
              <div class="section-header">
                <h3>{{ t('peakExtraction.slicePlots') }}</h3>
              </div>
              <div ref="qSliceDiv" class="chart-container"></div>
              <div ref="azSliceDiv" class="chart-container"></div>
            </div>

            <div v-if="mode === 'rough'" class="section-card">
              <div class="section-header">
                <h3>{{ t('peakExtraction.findPeaks') }}</h3>
              </div>
            <div class="form-grid-2">
              <div class="form-row"><label>{{ t('peakExtraction.prominence') }}</label><input type="number" v-model.number="pfP.prominence" step="10" /></div>
              <div class="form-row"><label>{{ t('peakExtraction.width') }}</label><input type="number" v-model.number="pfP.width" step="0.1" /></div>
            </div>
            <button class="btn-primary" :disabled="!roughSel" @click="findPeaks">{{ t('peakExtraction.autoFindPeaks') }}</button>
            <div class="tip-text">{{ t('peakExtraction.autoFindPeaksTip') }}</div>
            <div v-if="foundPeaks" class="peak-info">
              {{ t('peakExtraction.qPeaks') }}: {{ foundPeaks.q_peaks.length }} | {{ t('peakExtraction.azPeaks') }}: {{ foundPeaks.az_peaks.length }}
            </div>
          </div>

          <div class="section-card">
            <div class="section-header">
              <h3>{{ t('peakExtraction.peakList') }}</h3>
            </div>
            <div class="selection-info">
              <span>q: <b>{{ selectedQ != null ? selectedQ.toFixed(5) : '—' }}</b></span>
              <span>Az: <b>{{ selectedAz != null ? selectedAz.toFixed(2) : '—' }}</b>°</span>
            </div>
            <div class="btn-row">
              <button class="btn-primary" :disabled="!canRecord" @click="recordPeaks">{{ t('peakExtraction.recordPeaks') }}</button>
              <button class="btn-outline-sm" @click="clearSelection">{{ t('common.clear') || t('visualizer.clear') || 'Clear' }}</button>
            </div>
          </div>
        </div>

        <div v-show="rtab === 'records'" class="tab-content">
          <div class="section-card">
            <div class="section-header">
              <h3>{{ t('peakExtraction.peakList') }} <span class="count-badge">{{ peakRecords.length }}</span></h3>
            </div>
            <ul class="record-list">
              <li v-for="(r, i) in peakRecords" :key="i" class="record-item">
                <span><b>{{ t('peakExtraction.peakLabel') }} {{ i+1 }}</b> q={{ r.q.toFixed(4) }} Az={{ r.azimuth.toFixed(2) }}° I={{ r.intensity.toFixed(0) }}</span>
                <button class="btn-danger-small" @click="deleteRecord(i)">✕</button>
              </li>
            </ul>
            <div class="btn-row">
              <button class="btn-danger" :disabled="!peakRecords.length" @click="clearRecords">{{ t('peakExtraction.clearRecords') }}</button>
              <a v-if="sessionId" :href="exportUrl" class="btn-outline" download>{{ t('peakExtraction.exportCsv') }}</a>
            </div>
          </div>

          <div class="section-card save-records-card">
            <div class="section-header">
              <h3>保存用户提取数据 <span class="count-badge">{{ visibleSavedRecords.length }}</span></h3>
            </div>
            <div class="save-records-form">
              <div class="form-field-stack save-record-name-field">
                <label for="int-save-record-name">记录集名称</label>
                <input
                  id="int-save-record-name"
                  v-model.trim="saveRecordName"
                  type="text"
                  class="input-small"
                  placeholder="例如：integrated-hdpe-session-1"
                />
              </div>
              <div class="btn-row save-record-actions">
                <button class="btn-primary" :disabled="!sessionId || isSavingRecords" @click="handleSaveRecords">
                  {{ isSavingRecords ? '保存中...' : '保存当前记录' }}
                </button>
                <button class="btn-outline" :disabled="isRefreshingSavedRecords" @click="fetchSavedRecords()">
                  {{ isRefreshingSavedRecords ? '刷新中...' : '刷新列表' }}
                </button>
              </div>
            </div>
            <p class="save-records-hint">列表按名称显示最近一次保存；若名称重复，会先给出覆盖提示，再保留最新版本用于重新加载。</p>
            <div v-if="saveFeedback.message" :class="['save-records-feedback', `is-${saveFeedback.type}`]">
              {{ saveFeedback.message }}
            </div>
            <div v-if="visibleSavedRecords.length" class="saved-record-list">
              <article v-for="item in visibleSavedRecords" :key="item.id" class="saved-record-item">
                <div class="saved-record-copy">
                  <div class="saved-record-heading">
                    <strong>{{ item.name }}</strong>
                    <span class="saved-record-source">来源：{{ savedRecordSourceLabel(item.namespace) }}</span>
                  </div>
                  <div class="saved-record-meta">
                    <span>时间：{{ formatSavedAt(item.saved_at) }}</span>
                    <span>条目数：{{ item.record_count }}</span>
                  </div>
                </div>
                <button
                  class="btn-outline"
                  :disabled="!sessionId || loadingRecordId === item.id"
                  @click="handleLoadSavedRecord(item)"
                >
                  {{ loadingRecordId === item.id ? '加载中...' : '重新加载' }}
                </button>
              </article>
            </div>
            <div v-else class="empty-saved-records">
              {{ isRefreshingSavedRecords ? '正在读取已保存记录...' : '还没有已保存的积分图提取记录。' }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <ConfirmDialog
      :visible="overwriteDialog.visible"
      :title="overwriteDialog.title"
      :message="overwriteDialog.message"
      :confirmText="overwriteDialog.confirmText"
      :cancelText="overwriteDialog.cancelText"
      type="danger"
      @confirm="confirmOverwrite(true)"
      @cancel="confirmOverwrite(false)"
    />
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { intApi } from '@/api/peakExtractionApi'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import ColormapRenderer from '@/utils/diffraction/ColormapRenderer'

const { t } = useI18n()

const emit = defineEmits(['status'])

const sessionId  = ref(null)
const heatmapDiv = ref(null)
const qSliceDiv  = ref(null)
const azSliceDiv = ref(null)

const zData  = ref([])
const qAxis  = ref([])
const azAxis = ref([])

const qMin = ref(0);  const qMax = ref(1)
const azMin = ref(-180); const azMax = ref(180)

const sliderMin  = ref(0); const sliderMax = ref(65535)
const contrastMin = ref(0); const contrastMax = ref(65535)
const colormap   = ref('灰度')
const colormapValues = ['灰度', '反转灰度', '热力图', '彩虹']
const colormaps  = computed(() => [
  { value: colormapValues[0], label: t('peakExtraction.gray') },
  { value: colormapValues[1], label: t('peakExtraction.invertedGray') },
  { value: colormapValues[2], label: t('peakExtraction.hot') },
  { value: colormapValues[3], label: t('peakExtraction.jet') },
])

const rtab = ref('analysis')
const mode = ref('precise')
const sliceCenter = ref(null)
const roughSel    = ref(null)
const sp = ref({ az_int_w: 1.0, q_int_w: 0.01, q_disp_r: 0.2, az_disp_r: 20.0 })
const pfP = ref({ prominence: 100, width: 1.0 })
const cropP = ref({ az_crop_enabled: false, convention: 'ccw', psi_offset: 0.0, az_crop_min: -30.0, az_crop_max: 120.0 })

const selectedQ  = ref(null)
const selectedAz = ref(null)
const foundPeaks = ref(null)

const peakRecords = ref([])
const saveRecordName = ref('')
const savedRecords = ref([])
const isSavingRecords = ref(false)
const isRefreshingSavedRecords = ref(false)
const loadingRecordId = ref('')
const saveFeedback = ref({ type: 'info', message: '' })
const overwriteDialog = ref({
  visible: false,
  title: '',
  message: '',
  confirmText: '继续保存',
  cancelText: '取消',
  resolver: null,
})
const exportUrl  = computed(() => sessionId.value ? intApi.exportCsv(sessionId.value) : '#')
const visibleSavedRecords = computed(() => {
  const latestByName = new Map()
  for (const item of savedRecords.value) {
    const key = normalizeRecordName(item.name)
    if (!latestByName.has(key)) latestByName.set(key, item)
  }
  return Array.from(latestByName.values())
})

let _qSliceInited = false
let _azSliceInited = false
let _heatmapEventsBound = false
let _emptyCropToastShown = false

const canRecord = computed(() => {
  if (mode.value === 'precise') return selectedQ.value != null && selectedAz.value != null
  return foundPeaks.value && (foundPeaks.value.q_peaks.length || foundPeaks.value.az_peaks.length)
})

const plotlyCmap = computed(() => ColormapRenderer.getPlotlyColorscale(colormap.value))

function normalizeRecordName(name) {
  return (name || '').trim().toLocaleLowerCase()
}

function savedRecordSourceLabel(namespace) {
  return namespace === 'integrated' ? '积分图峰提取' : namespace || '未知来源'
}

function formatSavedAt(value) {
  if (!value) return '—'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

function setSaveFeedback(type, message) {
  saveFeedback.value = { type, message }
}

function findSameNameRecord(name) {
  const normalized = normalizeRecordName(name)
  if (!normalized) return null
  return visibleSavedRecords.value.find(item => normalizeRecordName(item.name) === normalized) || null
}

function requestOverwriteConfirmation(existing) {
  return new Promise(resolve => {
    overwriteDialog.value = {
      visible: true,
      title: '确认同名覆盖保存',
      message: `已存在名称为“${existing.name}”的记录集（${formatSavedAt(existing.saved_at)}，${existing.record_count} 条）。继续保存后，列表会以这次保存的最新版本作为可重新加载项。`,
      confirmText: '继续保存',
      cancelText: '取消',
      resolver: resolve,
    }
  })
}

function confirmOverwrite(confirmed) {
  const resolver = overwriteDialog.value.resolver
  overwriteDialog.value = {
    visible: false,
    title: '',
    message: '',
    confirmText: '继续保存',
    cancelText: '取消',
    resolver: null,
  }
  resolver?.(confirmed)
}

async function fetchSavedRecords({ quiet = false } = {}) {
  if (!quiet) isRefreshingSavedRecords.value = true
  try {
    const { data } = await intApi.listSavedRecords()
    savedRecords.value = Array.isArray(data.items) ? data.items : []
  } catch (err) {
    if (!quiet) {
      const detail = err.response?.data?.detail || err.message
      setSaveFeedback('error', `读取已保存记录失败：${detail}`)
      window.$toast?.(detail, true)
    }
  } finally {
    if (!quiet) isRefreshingSavedRecords.value = false
  }
}

async function onLoadFile(e) {
  const file = e.target.files[0]; if (!file) return
  emit('status', `Loading ${file.name}…`)
  try {
    _heatmapEventsBound = false
    if (heatmapDiv.value) {
      import('plotly.js-dist-min').then(Plotly => Plotly.purge(heatmapDiv.value))
    }
    const { data } = await intApi.load(file)
    sessionId.value = data.session_id
    zData.value  = data.z_data
    qAxis.value  = data.q_axis
    azAxis.value = data.az_axis
    qMin.value = data.q_range[0];  qMax.value  = data.q_range[1]
    azMin.value = data.az_range[0]; azMax.value = data.az_range[1]
    sliderMin.value   = Math.floor(data.contrast_min)
    sliderMax.value   = Math.ceil(data.contrast_max)
    contrastMin.value = Math.floor(data.contrast_min)
    contrastMax.value = Math.ceil(data.contrast_max)
    peakRecords.value = []
    sliceCenter.value = null
    roughSel.value    = null
    foundPeaks.value  = null
    selectedQ.value   = null
    selectedAz.value  = null
    await nextTick()
    drawHeatmap()
    clearSlices()
    emit('status', `Loaded: ${file.name}`)
    window.$toast?.(`Loaded ${file.name}`)
    await fetchSavedRecords({ quiet: true })
  } catch(err) { window.$toast?.(err.response?.data?.detail || err.message, true) }
}

async function onImportInfo(e) {
  const file = e.target.files[0]; if (!file) return
  try {
    const { data } = await intApi.importInfo(file)
    const hasAll = data.q_min != null && data.q_max != null && data.az_min != null && data.az_max != null
    if (data.q_min != null) { qMin.value = data.q_min; qMax.value = data.q_max }
    if (data.az_min != null) { azMin.value = data.az_min; azMax.value = data.az_max }
    if (hasAll && sessionId.value) {
      await applyRanges()
      window.$toast?.('Coordinate info applied')
    } else {
      window.$toast?.('Coordinate info loaded')
    }
  } catch(err) { window.$toast?.(err.response?.data?.detail || err.message, true) }
}

async function applyRanges() {
  if (!sessionId.value) return
  try {
    const { data } = await intApi.setRanges({
      session_id: sessionId.value,
      q_min: qMin.value, q_max: qMax.value,
      az_min: azMin.value, az_max: azMax.value,
    })
    zData.value  = data.z_data
    qAxis.value  = data.q_axis
    azAxis.value = data.az_axis
    sliceCenter.value = null
    drawHeatmap()
    emit('status', `Range: q[${qMin.value},${qMax.value}] Az[${azMin.value}°,${azMax.value}°]`)
  } catch(err) { window.$toast?.(err.response?.data?.detail || err.message, true) }
}

function restoreView() {
  import('plotly.js-dist-min').then(Plotly => {
    const cropRange = getCropAzRange()
    let yRange = null
    if (!cropRange) {
      yRange = [azMin.value, azMax.value]
    } else if (!cropRange.wrap) {
      yRange = [cropRange.start, cropRange.end]
    }
    const layoutUpdate = { 'xaxis.range': [qMin.value, qMax.value] }
    if (yRange) layoutUpdate['yaxis.range'] = yRange
    Plotly.relayout(heatmapDiv.value, layoutUpdate)
  })
}

function drawHeatmap() {
  if (!zData.value.length) return
  import('plotly.js-dist-min').then(Plotly => {
    const filtered = getFilteredHeatmapData()
    const traces = buildTraces()
    const layout = buildLayout(filtered)
    Plotly.react(heatmapDiv.value, traces, layout, { responsive: true, displayModeBar: false, scrollZoom: true })
    notifyEmptyCropState(filtered.hasData)

    if (!_heatmapEventsBound) {
      heatmapDiv.value.on('plotly_click', ev => {
        const pt = ev.points[0]
        if (pt == null) return
        const q = pt.x, az = pt.y
        if (mode.value === 'precise') {
          sliceCenter.value = { q, az }
          selectedQ.value = null; selectedAz.value = null
          foundPeaks.value = null
          fetchSlices()
        }
      })

      heatmapDiv.value.on('plotly_selected', ev => {
        if (!ev?.range || mode.value !== 'rough') return
        roughSel.value = { q_min: ev.range.x[0], q_max: ev.range.x[1], az_min: ev.range.y[0], az_max: ev.range.y[1] }
        sliceCenter.value = { q: (roughSel.value.q_min + roughSel.value.q_max) / 2, az: (roughSel.value.az_min + roughSel.value.az_max) / 2 }
        selectedQ.value = null; selectedAz.value = null; foundPeaks.value = null
        fetchSlices()
      })

      _heatmapEventsBound = true
    }
  })
}

function buildTraces() {
  const filtered = getFilteredHeatmapData()
  const traces = [{
    type: 'heatmap',
    z: filtered.z,
    x: qAxis.value,
    y: filtered.az,
    colorscale: plotlyCmap.value,
    zmin: contrastMin.value,
    zmax: contrastMax.value,
    showscale: false,
    hovertemplate: 'q=%{x:.4f}<br>Az=%{y:.2f}°<br>I=%{z:.0f}<extra></extra>',
    connectgaps: false,
  }]

  if (peakRecords.value.length) {
    const recs = peakRecords.value.filter(r => isAzInCrop(r.azimuth))
    if (recs.length) {
      traces.push({
        type: 'scatter', mode: 'markers',
        x: recs.map(r => r.q),
        y: recs.map(r => r.azimuth),
        marker: { color: '#ff3300', size: 10, symbol: 'x', line: { width: 2 } },
        name: 'Recorded',
        showlegend: false,
        hoverinfo: 'skip',
      })
    }
  }

  return traces
}

function buildLayout(filtered = getFilteredHeatmapData()) {
  const cropRange = getCropAzRange()
  let yRange = null
  if (!cropRange) {
    yRange = [azMin.value, azMax.value]
  } else if (!cropRange.wrap) {
    yRange = [cropRange.start, cropRange.end]
  }

  const annotations = []
  if (!filtered.hasData) {
    annotations.push({
      xref: 'paper',
      yref: 'paper',
      x: 0.5,
      y: 0.5,
      text: t('peakExtraction.cropOutsideRange'),
      showarrow: false,
      font: { color: '#d8eeff', size: 15 },
      bgcolor: 'rgba(0,0,0,0.45)',
      bordercolor: 'rgba(122,214,251,0.5)',
      borderwidth: 1,
      borderpad: 6,
    })
  }
  if (peakRecords.value.length) {
    const recs = peakRecords.value.filter(r => isAzInCrop(r.azimuth))
    for (const r of recs) {
      const origIdx = peakRecords.value.indexOf(r)
      annotations.push({
        x: r.q,
        y: r.azimuth,
        text: `P${origIdx + 1}`,
        showarrow: false,
        font: { color: '#ffffff', size: 16, family: 'Arial Black, Arial, sans-serif' },
        bordercolor: '#ffffff',
        borderwidth: 1.5,
        borderpad: 2,
        bgcolor: 'rgba(0,0,0,0.55)',
        xanchor: 'center',
        yanchor: 'bottom',
        yshift: 12,
      })
    }
  }

  return {
    margin: { t: 30, b: 50, l: 55, r: 30 },
    xaxis: { title: 'q (Å⁻¹)' },
    yaxis: { title: 'Azimuth (°)' },
    title: { text: t('peakExtraction.integration2DTitle'), font: { size: 13 } },
    dragmode: mode.value === 'rough' ? 'select' : 'pan',
    legend: { x: 1, xanchor: 'right', y: 1 },
    annotations,
    uirevision: 'int-heatmap',
  }
}

let _refreshTimer = null
function refreshHeatmap() {
  clearTimeout(_refreshTimer)
  _refreshTimer = setTimeout(drawHeatmap, 200)
}

function notifyEmptyCropState(hasData) {
  if (!cropP.value.az_crop_enabled) {
    _emptyCropToastShown = false
    return
  }
  if (!hasData) {
    if (!_emptyCropToastShown) {
      window.$toast?.(t('peakExtraction.cropOutsideRange'))
      _emptyCropToastShown = true
    }
    return
  }
  _emptyCropToastShown = false
}

async function fetchSlices() {
  if (!sessionId.value || !sliceCenter.value) return
  try {
    const { data } = await intApi.getSlice({
      session_id: sessionId.value,
      center_q: sliceCenter.value.q,
      center_az: sliceCenter.value.az,
      az_int_width: sp.value.az_int_w,
      q_int_width: sp.value.q_int_w,
      q_display_range: sp.value.q_disp_r,
      az_display_range: sp.value.az_disp_r,
      az_crop_enabled: cropP.value.az_crop_enabled,
      az_crop_min: cropP.value.az_crop_min,
      az_crop_max: cropP.value.az_crop_max,
      convention: cropP.value.convention,
      psi_offset: cropP.value.psi_offset,
    })
    await nextTick()
    if (data.empty_crop) {
      window.$toast?.(t('peakExtraction.cropOutsideRange'))
    }
    drawSlices(data)
  } catch(err) { console.warn(err) }
}

function drawSlices(d) {
  import('plotly.js-dist-min').then(Plotly => {
    const _sliceLayout = (title, xTitle) => ({
      shapes: [],
      margin: { t: 28, b: 36, l: 48, r: 8 },
      height: 200,
      title: { text: title, font: { size: 11 } },
      xaxis: { title: xTitle, titlefont: { size: 10 }, fixedrange: true },
      yaxis: { title: 'Intensity', titlefont: { size: 10 }, fixedrange: true },
      showlegend: false,
      dragmode: false,
      hovermode: 'closest',
    })
    const _sliceConfig = {
      responsive: true,
      displayModeBar: false,
      scrollZoom: false,
      doubleClick: false,
      staticPlot: false,
    }

    const qSel = selectedQ.value != null ? [{ type: 'line', x0: selectedQ.value, x1: selectedQ.value, y0: 0, y1: 1, yref: 'paper', line: { color: 'green', width: 2 } }] : []
    const qFoundLines = (foundPeaks.value?.q_peaks || []).map(p => ({ type: 'line', x0: p.q, x1: p.q, y0: 0, y1: 1, yref: 'paper', line: { color: 'purple', dash: 'dot', width: 1.5 } }))
    const qRefLine = sliceCenter.value ? [{ type: 'line', x0: sliceCenter.value.q, x1: sliceCenter.value.q, y0: 0, y1: 1, yref: 'paper', line: { color: 'red', dash: 'dash' } }] : []
    const qTrace = {
      x: d.q_values, y: d.i_q,
      mode: 'lines+markers',
      line: { color: '#2499f8', width: 2 },
      marker: { size: 5, color: '#2499f8', opacity: 0.7 },
      name: 'q-slice',
      hovertemplate: 'q=%{x:.5f}<br>I=%{y:.0f}<extra></extra>',
      connectgaps: false,
    }
    const denseQ = _interpDense(d.q_values, d.i_q, 3000)
    const qDenseTrace = {
      x: denseQ.x, y: denseQ.y,
      mode: 'markers',
      marker: { size: 8, color: 'transparent', opacity: 0 },
      name: '_q_dense',
      hoverinfo: 'skip',
      showlegend: false,
    }
    if (!_qSliceInited) {
      Plotly.newPlot(qSliceDiv.value, [qTrace, qDenseTrace], _sliceLayout(`Intensity vs q (Az≈${sliceCenter.value?.az.toFixed(1)}°)`, 'q (Å⁻¹)'), _sliceConfig)
      _qSliceInited = true
      _addFreeClickListener(qSliceDiv.value, xVal => {
        if (mode.value === 'precise') {
          selectedQ.value = xVal
          fetchSlices()
        }
      })
    } else {
      Plotly.react(qSliceDiv.value, [qTrace, qDenseTrace], _sliceLayout(`Intensity vs q (Az≈${sliceCenter.value?.az.toFixed(1)}°)`, 'q (Å⁻¹)'), _sliceConfig)
    }
    Plotly.relayout(qSliceDiv.value, { shapes: [...qRefLine, ...qSel, ...qFoundLines] })

    const azSel = selectedAz.value != null ? [{ type: 'line', x0: selectedAz.value, x1: selectedAz.value, y0: 0, y1: 1, yref: 'paper', line: { color: 'green', width: 2 } }] : []
    const azFoundLines = (foundPeaks.value?.az_peaks || []).map(p => ({ type: 'line', x0: p.azimuth, x1: p.azimuth, y0: 0, y1: 1, yref: 'paper', line: { color: 'purple', dash: 'dot', width: 1.5 } }))
    const azRefLine = sliceCenter.value ? [{ type: 'line', x0: sliceCenter.value.az, x1: sliceCenter.value.az, y0: 0, y1: 1, yref: 'paper', line: { color: 'red', dash: 'dash' } }] : []
    const azTrace = {
      x: d.az_values, y: d.i_az,
      mode: 'lines+markers',
      line: { color: '#27ae60', width: 2 },
      marker: { size: 5, color: '#27ae60', opacity: 0.7 },
      name: 'az-slice',
      hovertemplate: 'Az=%{x:.2f}°<br>I=%{y:.0f}<extra></extra>',
      connectgaps: false,
    }
    const denseAz = _interpDense(d.az_values, d.i_az, 3000)
    const azDenseTrace = {
      x: denseAz.x, y: denseAz.y,
      mode: 'markers',
      marker: { size: 8, color: 'transparent', opacity: 0 },
      name: '_az_dense',
      hoverinfo: 'skip',
      showlegend: false,
    }
    if (!_azSliceInited) {
      Plotly.newPlot(azSliceDiv.value, [azTrace, azDenseTrace], _sliceLayout(`Intensity vs Az (q≈${sliceCenter.value?.q.toFixed(4)})`, 'Azimuth (°)'), _sliceConfig)
      _azSliceInited = true
      _addFreeClickListener(azSliceDiv.value, xVal => {
        if (mode.value === 'precise') {
          selectedAz.value = xVal
          fetchSlices()
        }
      })
    } else {
      Plotly.react(azSliceDiv.value, [azTrace, azDenseTrace], _sliceLayout(`Intensity vs Az (q≈${sliceCenter.value?.q.toFixed(4)})`, 'Azimuth (°)'), _sliceConfig)
    }
    Plotly.relayout(azSliceDiv.value, { shapes: [...azRefLine, ...azSel, ...azFoundLines] })
  })
}

function normalizeAngle180(a) {
  let x = ((a % 360) + 360) % 360
  return x >= 180 ? x - 360 : x
}

function relativeCropToAz(psiLike) {
  const az = cropP.value.convention === 'ccw'
    ? (-psiLike + cropP.value.psi_offset)
    : (psiLike + cropP.value.psi_offset)
  return normalizeAngle180(az)
}

function isAzInCrop(az) {
  if (!cropP.value.az_crop_enabled) return true
  const azNorm = normalizeAngle180(az)
  const start = relativeCropToAz(cropP.value.az_crop_min)
  const end   = relativeCropToAz(cropP.value.az_crop_max)
  if (start <= end) return azNorm >= start && azNorm <= end
  return azNorm >= start || azNorm <= end
}

function getCropAzRange() {
  if (!cropP.value.az_crop_enabled) return null
  const start = relativeCropToAz(cropP.value.az_crop_min)
  const end   = relativeCropToAz(cropP.value.az_crop_max)
  return { start, end, wrap: start > end }
}

function getFilteredHeatmapData() {
  const az = [...azAxis.value]
  const z = azAxis.value.map((azValue, rowIndex) => {
    if (isAzInCrop(azValue)) return [...(zData.value[rowIndex] || [])]
    const row = zData.value[rowIndex] || []
    return row.map(() => null)
  })
  const hasData = azAxis.value.some(azValue => isAzInCrop(azValue))
  return { az, z, hasData }
}

function _addFreeClickListener(el, onPick) {
  function handler(e) {
    const layout = el._fullLayout
    if (!layout) return
    const xaxis = layout.xaxis
    const rect = el.getBoundingClientRect()
    const xPixel = e.clientX - rect.left - xaxis._offset
    if (xPixel < 0 || xPixel > xaxis._length) return
    onPick(xaxis.p2d(xPixel))
  }
  el.addEventListener('click', handler)
  return () => el.removeEventListener('click', handler)
}

function _interpDense(xs, ys, n) {
  if (!xs || xs.length < 2) return { x: xs || [], y: ys || [] }
  const xMin = xs[0], xMax = xs[xs.length - 1]
  const dx = (xMax - xMin) / (n - 1)
  const denseX = [], denseY = []
  for (let i = 0; i < n; i++) {
    const x = xMin + i * dx
    let lo = 0, hi = xs.length - 1
    while (lo < hi - 1) { const mid = (lo + hi) >> 1; xs[mid] <= x ? lo = mid : hi = mid }
    const t = hi > lo ? (x - xs[lo]) / (xs[hi] - xs[lo]) : 0
    denseX.push(x)
    denseY.push(ys[lo] + t * (ys[hi] - ys[lo]))
  }
  return { x: denseX, y: denseY }
}

function clearSlices() {
  import('plotly.js-dist-min').then(Plotly => {
    if (_qSliceInited) { Plotly.purge(qSliceDiv.value); _qSliceInited = false }
    if (_azSliceInited) { Plotly.purge(azSliceDiv.value); _azSliceInited = false }
  })
}

function setMode(m) {
  mode.value = m
  clearSelection()
  import('plotly.js-dist-min').then(Plotly => {
    Plotly.relayout(heatmapDiv.value, { dragmode: m === 'rough' ? 'select' : 'pan' })
  })
}

function clearSelection() {
  sliceCenter.value = null; roughSel.value = null
  selectedQ.value = null; selectedAz.value = null; foundPeaks.value = null
  clearSlices()
}

function onCropChange() {
  sliceCenter.value = null
  roughSel.value = null
  selectedQ.value = null
  selectedAz.value = null
  foundPeaks.value = null
  drawHeatmap()
}

watch(cropP, onCropChange, { deep: true })

async function findPeaks() {
  if (!sessionId.value || !roughSel.value) return
  try {
    const { data } = await intApi.findPeaks({
      session_id: sessionId.value,
      ...roughSel.value,
      prominence: pfP.value.prominence,
      width: pfP.value.width,
      az_crop_enabled: cropP.value.az_crop_enabled,
      az_crop_min: cropP.value.az_crop_min,
      az_crop_max: cropP.value.az_crop_max,
      convention: cropP.value.convention,
      psi_offset: cropP.value.psi_offset,
    })
    foundPeaks.value = data
    if (data.empty_crop) {
      window.$toast?.(t('peakExtraction.cropOutsideRange'))
    }
    await fetchSlices()
    emit('status', `q peaks: ${data.q_peaks.length} | Az peaks: ${data.az_peaks.length}`)
  } catch(err) { window.$toast?.(err.response?.data?.detail || err.message, true) }
}

async function recordPeaks() {
  if (!sessionId.value) return
  let peaks = []
  if (mode.value === 'precise') {
    if (selectedQ.value == null || selectedAz.value == null) return
    peaks = [{ q: selectedQ.value, azimuth: selectedAz.value }]
  } else {
    const qp = foundPeaks.value?.q_peaks || []
    const ap = foundPeaks.value?.az_peaks || []
    if (qp.length && ap.length) {
      for (const q of qp) for (const a of ap) peaks.push({ q: q.q, azimuth: a.azimuth })
    } else if (qp.length) peaks = qp.map(p => ({ q: p.q, azimuth: sliceCenter.value?.az ?? 0 }))
    else if (ap.length) peaks = ap.map(p => ({ q: sliceCenter.value?.q ?? 0, azimuth: p.azimuth }))
  }
  if (!peaks.length) return
  try {
    const { data } = await intApi.recordPeaks({ session_id: sessionId.value, peaks })
    peakRecords.value = data.records
    refreshHeatmap()
    window.$toast?.(`Recorded ${peaks.length} peaks`)
  } catch(err) { window.$toast?.(err.response?.data?.detail || err.message, true) }
}

async function deleteRecord(idx) {
  if (!sessionId.value) return
  const { data } = await intApi.deleteRecord({ session_id: sessionId.value, index: idx })
  peakRecords.value = data.records
  refreshHeatmap()
}

async function clearRecords() {
  if (!sessionId.value) return
  await intApi.clearRecords(sessionId.value)
  peakRecords.value = []
  refreshHeatmap()
}

async function handleSaveRecords() {
  if (!sessionId.value) {
    const message = '请先载入积分图，再保存提取记录。'
    setSaveFeedback('warning', message)
    window.$toast?.(message, true)
    return
  }
  if (!peakRecords.value.length) {
    const message = '当前没有可保存的提取记录。'
    setSaveFeedback('warning', message)
    window.$toast?.(message, true)
    return
  }

  const name = saveRecordName.value.trim()
  const sameNameRecord = findSameNameRecord(name)
  if (sameNameRecord) {
    const confirmed = await requestOverwriteConfirmation(sameNameRecord)
    if (!confirmed) {
      setSaveFeedback('info', `已取消保存“${sameNameRecord.name}”的新版本。`)
      return
    }
  }

  isSavingRecords.value = true
  try {
    const { data } = await intApi.saveRecords({ session_id: sessionId.value, name })
    const savedRecord = data.saved_record
    await fetchSavedRecords({ quiet: true })
    saveRecordName.value = savedRecord?.name || name
    setSaveFeedback('success', `已保存“${savedRecord?.name || '未命名记录集'}”，共 ${savedRecord?.record_count ?? peakRecords.value.length} 条记录。`)
    window.$toast?.(`已保存记录集：${savedRecord?.name || '未命名记录集'}`)
  } catch (err) {
    const detail = err.response?.data?.detail || err.message
    setSaveFeedback('error', `保存失败：${detail}`)
    window.$toast?.(detail, true)
  } finally {
    isSavingRecords.value = false
  }
}

async function handleLoadSavedRecord(item) {
  if (!sessionId.value) {
    const message = '请先载入积分图，再加载已保存记录。'
    setSaveFeedback('warning', message)
    window.$toast?.(message, true)
    return
  }

  loadingRecordId.value = item.id
  try {
    const { data } = await intApi.loadRecords({ session_id: sessionId.value, record_id: item.id })
    peakRecords.value = Array.isArray(data.records) ? data.records : []
    saveRecordName.value = item.name || saveRecordName.value
    rtab.value = 'records'
    refreshHeatmap()
    const loaded = data.loaded_record || item
    setSaveFeedback('success', `已加载“${loaded.name || item.name}”，共 ${loaded.record_count ?? peakRecords.value.length} 条记录。`)
    emit('status', `Loaded saved integrated records: ${loaded.name || item.name}`)
    window.$toast?.(`已加载记录集：${loaded.name || item.name}`)
  } catch (err) {
    const detail = err.response?.data?.detail || err.message
    setSaveFeedback('error', `加载失败：${detail}`)
    window.$toast?.(detail, true)
  } finally {
    loadingRecordId.value = ''
  }
}

onMounted(() => {
  fetchSavedRecords()
})
</script>

<style scoped>
.int-view {
  height: 100%;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  height: 100%;
}

.heatmap-section {
  grid-column: 1 / -1;
  min-width: 0;
}

.left-panel, .right-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.right-panel {
  min-width: 0;
}

.section-card {
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 16px;
}

.section-header {
  margin-bottom: 12px;
}

.section-header h3 {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary);
  overflow-wrap: anywhere;
}

.heatmap-container {
  width: 100%;
  height: 45vh;
  background: #111;
  border-radius: var(--radius-md);
}

.chart-container {
  margin-top: 8px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.form-row label {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  min-width: 130px;
  flex-shrink: 0;
  white-space: nowrap;
}

.form-row.compact {
  margin-top: 8px;
}

.value-badge {
  background: var(--primary-bg);
  color: var(--primary);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  min-width: 50px;
  text-align: center;
}

.select-small {
  padding: 4px 8px;
  font-size: 0.8125rem;
}

.select-medium {
  padding: 6px 8px;
  font-size: 0.8125rem;
}

.input-small {
  width: 80px;
  padding: 6px 8px;
  font-size: 0.8125rem;
}

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.tab-bar {
  display: flex;
  gap: 4px;
  background: var(--bg-surface-alt);
  padding: 4px;
  border-radius: var(--radius-md);
  margin-bottom: 4px;
}

.tab-btn {
  flex: 1;
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.tab-btn:hover {
  color: var(--text-primary);
}

.tab-btn.active {
  background: var(--bg-surface);
  color: var(--primary);
  box-shadow: var(--shadow-sm);
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.btn-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-row {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.btn-primary {
  background: var(--primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: 8px 16px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-primary:hover {
  background: var(--primary-light);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: default;
}

.btn-secondary {
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-surface-alt);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 8px 14px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-secondary:hover {
  background: var(--bg-hover);
  border-color: var(--border-hover);
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.btn-outline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 8px 14px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  text-decoration: none;
}

.btn-outline:hover {
  background: var(--bg-surface-alt);
}

.btn-outline-sm {
  background: transparent;
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 6px 12px;
  font-size: 0.8125rem;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-outline-sm:hover {
  background: var(--bg-surface-alt);
}

.btn-toggle {
  background: var(--bg-surface-alt);
  color: var(--text-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 8px 16px;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-toggle.active {
  background: var(--primary-bg);
  color: var(--primary);
  border-color: var(--primary);
}

.btn-danger {
  background: var(--error);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  padding: 8px 16px;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-danger:hover {
  opacity: 0.9;
}

.btn-danger:disabled {
  opacity: 0.5;
  cursor: default;
}

.btn-danger-small {
  background: var(--error);
  color: white;
  border: none;
  border-radius: 4px;
  padding: 2px 8px;
  font-size: 0.75rem;
  cursor: pointer;
}

.slice-info, .peak-info, .hint-text, .tip-text {
  margin-top: 10px;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.selection-info {
  display: flex;
  gap: 16px;
  font-size: 0.8125rem;
  margin-bottom: 10px;
}

.record-list {
  list-style: none;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.record-item {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  font-size: 0.8125rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.record-item:last-child {
  border-bottom: none;
}

.record-item:hover {
  background: var(--bg-surface-alt);
}

.count-badge {
  background: var(--primary);
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 0.75rem;
  font-weight: 600;
}

.save-records-card {
  gap: 12px;
}

.save-records-form {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.save-record-name-field {
  flex: 1 1 240px;
}

.save-record-actions {
  margin-top: 0;
}

.save-records-hint {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.save-records-feedback {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  font-size: 0.8125rem;
}

.save-records-feedback.is-success {
  background: rgba(16, 185, 129, 0.08);
  border-color: rgba(16, 185, 129, 0.35);
  color: #0f766e;
}

.save-records-feedback.is-warning {
  background: rgba(245, 158, 11, 0.1);
  border-color: rgba(245, 158, 11, 0.35);
  color: #92400e;
}

.save-records-feedback.is-error {
  background: rgba(239, 68, 68, 0.08);
  border-color: rgba(239, 68, 68, 0.3);
  color: #b91c1c;
}

.save-records-feedback.is-info {
  background: var(--primary-bg);
  border-color: rgba(30, 64, 175, 0.2);
  color: var(--primary);
}

.saved-record-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.saved-record-item {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
  background: var(--bg-surface-alt);
}

.saved-record-copy {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.saved-record-heading {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  font-size: 0.875rem;
}

.saved-record-source {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--primary-bg);
  color: var(--primary);
  font-size: 0.75rem;
  font-weight: 600;
}

.saved-record-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.empty-saved-records {
  border: 1px dashed var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
  color: var(--text-secondary);
  font-size: 0.8125rem;
  background: var(--bg-surface-alt);
}
</style>
