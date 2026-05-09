<template>
  <div class="raw-view">
    <div class="content-grid">
      <div class="left-panel">
        <div class="section-card raw-image-section">
          <div class="section-header">
            <h3>{{ t('visualizer.rawImage') }}</h3>
          </div>
          <ImageCanvas
            ref="imageCanvasRef"
            :image-src="imageB64"
            :orig-width="origWidth"
            :orig-height="origHeight"
            :disp-width="dispWidth"
            :disp-height="dispHeight"
            :markers="markerList"
            :center-x="params.center_x"
            :center-y="params.center_y"
            @click="onMainClick"
            class="image-canvas-wrapper"
          />
        </div>

        <div class="section-card">
          <div class="section-header">
            <h3>{{ t('peakExtraction.contrast') }}</h3>
          </div>
          <div class="form-group">
            <div class="form-row">
              <label>{{ t('peakExtraction.contrastMin') }}</label>
              <input type="range" :min="sliderMin" :max="sliderMax" v-model.number="contrastMin" @input="debouncedRender" />
              <input type="number" :min="sliderMin" :max="contrastMax" v-model.number="contrastMin" @input="debouncedRender" class="contrast-num" />
            </div>
            <div class="form-row">
              <label>{{ t('peakExtraction.contrastMax') }}</label>
              <input type="range" :min="sliderMin" :max="sliderMax" v-model.number="contrastMax" @input="debouncedRender" />
              <input type="number" :min="contrastMin" :max="sliderMax" v-model.number="contrastMax" @input="debouncedRender" class="contrast-num" />
            </div>
            <div class="form-row compact">
              <label>{{ t('peakExtraction.colormap') }}</label>
              <select v-model="colormap" @change="debouncedRender" class="select-small">
                <option v-for="c in colormaps" :key="c.value" :value="c.value">{{ c.label }}</option>
              </select>
              <label>Zoom</label>
              <select v-model.number="zoomSize" class="select-small">
                <option :value="30">30×30</option>
                <option :value="50">50×50</option>
                <option :value="100">100×100</option>
              </select>
            </div>
          </div>
        </div>

        <div class="section-card integrate-qi-section">
          <div class="section-header">
            <h3 class="section-title-stack">
              <span>{{ t('peakExtraction.integrateRegion') }}</span>
              <span class="section-title-subline">q-I</span>
            </h3>
          </div>
          <div class="form-grid-3">
            <div class="form-field-stack"><label>{{ t('peakExtraction.azimuthRange') }}</label><input type="number" v-model.number="intP.azimuth_range_half" step="1" @change="runIntegration" /></div>
            <div class="form-field-stack"><label>{{ t('peakExtraction.radialRange') }}</label><input type="number" v-model.number="intP.radial_range_half" step="0.01" @change="runIntegration" /></div>
            <div class="form-field-stack"><label>Q Points</label><input type="number" v-model.number="intP.npt" step="50" @change="runIntegration" /></div>
          </div>
        </div>

        <div class="section-card integrate-qi-section">
          <div class="section-header">
            <h3 class="section-title-stack">
              <span>{{ t('peakExtraction.integrateRegion') }}</span>
              <span class="section-title-subline">ψ-I</span>
            </h3>
          </div>
          <div class="form-grid-3">
            <div class="form-field-stack"><label>{{ t('peakExtraction.azimuthRange') }}</label><input type="number" v-model.number="intP.azimuth_range_half_r" step="5" @change="runIntegration" /></div>
            <div class="form-field-stack"><label>{{ t('peakExtraction.radialRange') }}</label><input type="number" v-model.number="intP.radial_range_half_r" step="0.01" @change="runIntegration" /></div>
            <div class="form-field-stack"><label>Psi Points</label><input type="number" v-model.number="intP.npt_rad_r" step="10" @change="runIntegration" /></div>
          </div>
        </div>
      </div>

      <div class="right-panel">
        <div class="tab-bar">
          <button :class="['tab-btn', { active: rtab === 'settings' }]" @click="rtab = 'settings'">{{ t('params.parameters') }}</button>
          <button :class="['tab-btn', { active: rtab === 'analysis' }]" @click="rtab = 'analysis'">{{ t('nav.analysis') }}</button>
          <button :class="['tab-btn', { active: rtab === 'records' }]" @click="rtab = 'records'">{{ t('peakExtraction.recordedPoints') }}</button>
        </div>

        <div v-show="rtab === 'settings'" class="tab-content">
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
                <input type="file" accept=".edf,.tiff,.tif" @change="onLoadFile" hidden />
              </label>
              <label class="btn-secondary">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="btn-icon">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                  <polyline points="14,2 14,8 20,8"/>
                </svg>
                {{ t('peakExtraction.loadPoni') }}
                <input type="file" accept=".poni" @change="onImportPoni" hidden />
              </label>
            </div>
          </div>

          <div class="section-card">
            <div class="section-header">
              <h3>{{ t('peakExtraction.applyThreshold') }}</h3>
            </div>
            <div class="form-row">
              <label>{{ t('peakExtraction.contrastMin') }}</label>
              <input type="number" v-model.number="threshMin" class="input-small" />
              <label>{{ t('peakExtraction.contrastMax') }}</label>
              <input type="number" v-model.number="threshMax" class="input-small" />
            </div>
            <div class="btn-group compact">
              <button class="btn-primary" @click="applyThreshold">{{ t('peakExtraction.applyParams') }}</button>
              <!-- BUG FIX: autoThreshold now resets to the values returned at load time -->
              <button class="btn-outline" @click="autoThreshold">{{ t('peakExtraction.autoThreshold') }}</button>
            </div>
          </div>

          <div class="section-card instrument-params-card">
            <div class="section-header">
              <h3>{{ t('peakExtraction.instrumentParams') }}</h3>
            </div>
            <div class="form-grid-2 instrument-params-grid">
              <div class="form-field-stack"><label>{{ t('peakExtraction.wavelength') }}</label><input type="number" v-model.number="params.wavelength" step="0.0001" /></div>
              <div class="form-field-stack"><label>{{ t('peakExtraction.distance') }}</label><input type="number" v-model.number="params.distance" step="1" /></div>
              <div class="form-field-stack"><label>{{ t('peakExtraction.pixelSizeX') }}</label><input type="number" v-model.number="params.pixel_size_x" step="1" /></div>
              <div class="form-field-stack"><label>{{ t('peakExtraction.pixelSizeY') }}</label><input type="number" v-model.number="params.pixel_size_y" step="1" /></div>
              <div class="form-field-stack"><label>{{ t('peakExtraction.centerX') }}</label><input type="number" v-model.number="params.center_x" step="0.1" /></div>
              <div class="form-field-stack"><label>{{ t('peakExtraction.centerY') }}</label><input type="number" v-model.number="params.center_y" step="0.1" /></div>
            </div>
          </div>
        </div>

        <div v-show="rtab === 'analysis'" class="tab-content">
          <div class="section-card">
            <div class="section-header">
              <h3>{{ t('peakExtraction.zoomClick') }}</h3>
            </div>
            <div class="zoom-container">
              <div class="zoom-image">
                <img v-if="zoomB64" :src="'data:image/png;base64,' + zoomB64" @click="onZoomClick" ref="zoomImgRef" />
                <div v-else class="zoom-placeholder">{{ t('peakExtraction.clickToSelect') }}</div>
              </div>
              <div class="zoom-info">
                <div v-if="currentPoint" class="point-info">
                  <div><span class="label">{{ t('peakExtraction.pixel') }}:</span> <b>({{ currentPoint.x }}, {{ currentPoint.y }})</b></div>
                  <div><span class="label">{{ t('peakExtraction.intensity') }}:</span> <b>{{ currentPoint.intensity?.toFixed(1) }}</b></div>
                  <div><span class="label">q:</span> <b>{{ currentPoint.q?.toFixed(5) }}</b> Å⁻¹</div>
                  <div><span class="label">ψ:</span> <b>{{ currentPoint.psi_deg?.toFixed(2) }}</b>°</div>
                </div>
                <div v-else class="dimmed">{{ t('peakExtraction.clickToSelect') }}</div>
                <button class="btn-primary" :disabled="!currentPoint" @click="recordPoint">{{ t('peakExtraction.recordPoint') }}</button>
              </div>
            </div>
          </div>

          <div v-if="intData" class="section-card">
            <div class="section-header">
              <h3>{{ t('peakExtraction.integrate') }}</h3>
            </div>
            <!-- BUG FIX: chart click hint -->
            <p class="chart-hint">{{ t('peakExtraction.clickChartToSelect') || 'Click on the curve to select a point' }}</p>
            <div ref="chartQ" class="chart-container"></div>
            <div ref="chartPsi" class="chart-container"></div>
            <div class="selection-info">
              <span>Selected q: <b>{{ selectedQ != null ? selectedQ.toFixed(5) : '—' }}</b></span>
              <span>Selected ψ: <b>{{ selectedPsi != null ? selectedPsi.toFixed(2) : '—' }}</b></span>
              <button class="btn-primary" :disabled="!sessionId" @click="calcNewPixel">{{ t('peakExtraction.refinePeak') }}</button>
            </div>
          </div>
          <div v-else-if="sessionId" class="section-card dimmed" style="text-align:center;">
            {{ t('peakExtraction.clickToSelect') }}
          </div>
        </div>

        <div v-show="rtab === 'records'" class="tab-content">
          <div class="section-card">
            <div class="section-header">
              <h3>{{ t('peakExtraction.recordedPoints') }} <span class="count-badge">{{ records.length }}</span></h3>
            </div>
            <!-- ψ offset correction -->
            <div class="form-row" style="margin-bottom:10px;">
              <label style="min-width:80px;">ψ offset (°)</label>
              <input type="number" v-model.number="psiOffset" step="0.1" style="width:90px;" />
              <span class="dimmed" style="font-size:0.75rem; margin-left:6px;">corrected = raw − offset</span>
            </div>
            <ul class="record-list">
              <li v-for="(r, i) in records" :key="i" class="record-item">
                <span>
                  <b>Point {{ i+1 }}</b> ({{ r.x }}, {{ r.y }})
                  q={{ r.q.toFixed(4) }}
                  ψ<sub>raw</sub>={{ r.psi_deg.toFixed(2) }}°
                  <span v-if="psiOffset !== 0" style="color:var(--primary)">
                    → ψ<sub>corr</sub>={{ (r.psi_deg - psiOffset).toFixed(2) }}°
                  </span>
                </span>
                <button class="btn-danger-small" @click="deleteRecord(i)">✕</button>
              </li>
            </ul>
            <div class="btn-group compact">
              <button class="btn-danger" :disabled="!records.length" @click="clearRecords">{{ t('peakExtraction.clearRecords') }}</button>
              <a v-if="sessionId" :href="exportUrl" class="btn-outline" download>{{ t('peakExtraction.exportCsv') }}</a>
              <a v-if="sessionId" :href="exportTxtUrl" class="btn-outline" download style="color:var(--primary);">Export TXT</a>
            </div>
          </div>

          <div class="section-card save-records-card">
            <div class="section-header">
              <h3>保存用户提取数据 <span class="count-badge">{{ visibleSavedRecords.length }}</span></h3>
            </div>
            <div class="save-records-form">
              <div class="form-field-stack save-record-name-field">
                <label for="raw-save-record-name">记录集名称</label>
                <input
                  id="raw-save-record-name"
                  v-model.trim="saveRecordName"
                  type="text"
                  class="input-small"
                  placeholder="例如：raw-hdpe-session-1"
                />
              </div>
              <div class="btn-group save-record-actions">
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
              {{ isRefreshingSavedRecords ? '正在读取已保存记录...' : '还没有已保存的原始图提取记录。' }}
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
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { rawApi } from '@/api/peakExtractionApi'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import ImageCanvas from './ImageCanvas.vue'

const { t } = useI18n()

const emit = defineEmits(['status'])

const sessionId  = ref(null)
const imageB64   = ref(null)
const origWidth  = ref(1)
const origHeight = ref(1)
const dispWidth  = ref(1)
const dispHeight = ref(1)
const sliderMin  = ref(0)
const sliderMax  = ref(65535)
const contrastMin = ref(0)
const contrastMax = ref(65535)
const colormap   = ref('灰度')
const colormapKeys = ['gray', 'inverted_gray', 'hot', 'jet']
const colormapValues = ['灰度', '反转灰度', '热力图', '彩虹']
const colormaps  = computed(() => [
  { value: colormapValues[0], label: t('peakExtraction.gray') },
  { value: colormapValues[1], label: t('peakExtraction.invertedGray') },
  { value: colormapValues[2], label: t('peakExtraction.hot') },
  { value: colormapValues[3], label: t('peakExtraction.jet') },
])
const zoomSize   = ref(30)
const threshMin  = ref(0)
const threshMax  = ref(65535)
// BUG FIX: remember the auto-detected threshold so autoThreshold() can restore it
const autoThreshMin = ref(0)
const autoThreshMax = ref(65535)
const rtab       = ref('settings')

const params = ref({ wavelength: 1.0, pixel_size_x: 100, pixel_size_y: 100, center_x: 0, center_y: 0, distance: 1000 })
// ψ offset: corrected_psi = raw_psi_deg - psiOffset
// e.g. if equator appears at +10°, set offset = 10 → corrected = 0°
const psiOffset = ref(0)
const intP   = ref({ azimuth_range_half: 5, radial_range_half: 0.35, npt: 500, npt_rad: 30, azimuth_range_half_r: 30, radial_range_half_r: 0.05, npt_r: 50, npt_rad_r: 150 })

const zoomB64    = ref(null)
const currentPoint = ref(null)
const records    = ref([])
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

const intData    = ref(null)
const selectedQ  = ref(null)
const selectedPsi = ref(null)

const chartQ   = ref(null)
const chartPsi = ref(null)
const zoomImgRef = ref(null)
const imageCanvasRef = ref(null)

// BUG FIX: track whether Plotly charts have been initialised so we can
// destroy them cleanly and avoid stale event listeners
let _chartQInited = false
let _chartPsiInited = false

/**
 * Attach a free-click listener to a Plotly chart div.
 * Unlike plotly_click (which only fires on data markers), this converts
 * the raw mouse position to a data-axis value via Plotly's internal p2d(),
 * so the user can click anywhere along the curve or in empty space.
 *
 * @param {HTMLElement} el      - the chart container div
 * @param {Function}    onPick  - called with the x data-value of the click
 * @returns {Function}          - call this to remove the listener
 */
function _addFreeClickListener(el, onPick) {
  function handler(e) {
    const layout = el._fullLayout
    if (!layout) return
    const xaxis  = layout.xaxis
    // xaxis._offset = left edge of plot area in px (within the div)
    // xaxis._length = width of plot area in px
    const rect   = el.getBoundingClientRect()
    const xPixel = e.clientX - rect.left - xaxis._offset
    if (xPixel < 0 || xPixel > xaxis._length) return  // outside plot area
    onPick(xaxis.p2d(xPixel))
  }
  el.addEventListener('click', handler)
  return () => el.removeEventListener('click', handler)
}

const markerList = computed(() =>
  records.value.map((r, i) => ({ x: r.x, y: r.y, color: '#ff3300', label: `${i+1}` }))
)

const visibleSavedRecords = computed(() => {
  const latestByName = new Map()
  for (const item of savedRecords.value) {
    const key = normalizeRecordName(item.name)
    if (!latestByName.has(key)) latestByName.set(key, item)
  }
  return Array.from(latestByName.values())
})

const exportUrl    = computed(() => {
  if (!sessionId.value) return '#'
  const base = rawApi.exportCsv(sessionId.value)
  return psiOffset.value !== 0 ? `${base}?psi_offset=${psiOffset.value}` : base
})
const exportTxtUrl = computed(() => {
  if (!sessionId.value) return '#'
  // derive txt url from csv url pattern (replace /export-csv/ with /export-txt/)
  const base = rawApi.exportCsv(sessionId.value).replace('/export-csv/', '/export-txt/')
  return psiOffset.value !== 0 ? `${base}?psi_offset=${psiOffset.value}` : base
})

function normalizeRecordName(name) {
  return (name || '').trim().toLocaleLowerCase()
}

function savedRecordSourceLabel(namespace) {
  return namespace === 'raw' ? '原始图峰提取' : namespace || '未知来源'
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

function requestOverwriteConfirmation(existing, name) {
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
    const { data } = await rawApi.listSavedRecords()
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
    const { data } = await rawApi.load(file)
    sessionId.value  = data.session_id
    origWidth.value  = data.orig_width
    origHeight.value = data.orig_height
    dispWidth.value  = data.disp_width || data.orig_width
    dispHeight.value = data.disp_height || data.orig_height
    imageB64.value   = data.image_b64
    sliderMin.value  = Math.floor(data.contrast_min)
    sliderMax.value  = Math.ceil(data.contrast_max)
    contrastMin.value = Math.floor(data.contrast_min)
    contrastMax.value = Math.ceil(data.contrast_max)
    threshMin.value  = data.threshold_min
    threshMax.value  = data.threshold_max
    // BUG FIX: store auto values for reset
    autoThreshMin.value = data.threshold_min
    autoThreshMax.value = data.threshold_max
    records.value    = []
    intData.value    = null
    zoomB64.value    = null
    currentPoint.value = null
    _destroyCharts()
    await nextTick()
    imageCanvasRef.value?.resetView()
    emit('status', `Loaded: ${file.name} (${data.orig_width}×${data.orig_height})`)
    window.$toast?.(`Loaded ${file.name}`)
    await fetchSavedRecords({ quiet: true })
  } catch(err) {
    window.$toast?.(err.response?.data?.detail || err.message, true)
  }
}

async function onImportPoni(e) {
  const file = e.target.files[0]; if (!file) return
  try {
    const { data } = await rawApi.importPoni(file)
    params.value = { ...params.value, ...data }
    window.$toast?.('PONI file imported')
    emit('status', 'PONI parameters updated')
  } catch(err) {
    window.$toast?.(err.response?.data?.detail || err.message, true)
  }
}

let _renderTimer = null
function debouncedRender() {
  clearTimeout(_renderTimer)
  _renderTimer = setTimeout(doRender, 300)
}

async function doRender() {
  if (!sessionId.value) return
  try {
    const { data } = await rawApi.render({
      session_id: sessionId.value,
      colormap: colormap.value,
      contrast_min: contrastMin.value,
      contrast_max: contrastMax.value,
    })
    imageB64.value = data.image_b64
  } catch(err) { console.warn(err) }
}

async function applyThreshold() {
  if (!sessionId.value) return
  try {
    const { data } = await rawApi.applyThresh({
      session_id: sessionId.value,
      threshold_min: threshMin.value,
      threshold_max: threshMax.value,
      colormap: colormap.value,
      contrast_min: contrastMin.value,
      contrast_max: contrastMax.value,
    })
    imageB64.value = data.image_b64
    emit('status', `Threshold applied: ${threshMin.value} – ${threshMax.value}`)
  } catch(err) { window.$toast?.(err.response?.data?.detail || err.message, true) }
}

// BUG FIX: autoThreshold now correctly resets to auto-detected values and re-applies
async function autoThreshold() {
  threshMin.value = autoThreshMin.value
  threshMax.value = autoThreshMax.value
  await applyThreshold()
  emit('status', 'Reset to auto threshold')
}

async function onMainClick({ imageX, imageY }) {
  if (!sessionId.value) return
  try {
    const { data } = await rawApi.click({
      session_id: sessionId.value,
      image_x: imageX, image_y: imageY,
      zoom_size: zoomSize.value,
      colormap: colormap.value,
      contrast_min: contrastMin.value,
      contrast_max: contrastMax.value,
      ...params.value,
    })
    zoomB64.value = data.zoom_b64
    currentPoint.value = { x: data.max_x, y: data.max_y, intensity: data.intensity, q: data.q, psi_rad: data.psi_rad, psi_deg: data.psi_deg }
    rtab.value = 'analysis'
    emit('status', `Peak: (${data.max_x}, ${data.max_y}) q=${data.q.toFixed(5)} ψ=${data.psi_deg.toFixed(2)}°`)
    runIntegration()
  } catch(err) { window.$toast?.(err.response?.data?.detail || err.message, true) }
}

async function onZoomClick(e) {
  if (!sessionId.value || !currentPoint.value) return
  const rect = zoomImgRef.value.getBoundingClientRect()
  const localX = Math.round((e.clientX - rect.left) / rect.width * zoomSize.value)
  const localY = Math.round((e.clientY - rect.top) / rect.height * zoomSize.value)
  try {
    const { data } = await rawApi.zoomClick({
      session_id: sessionId.value,
      local_x: localX, local_y: localY,
      center_x_img: currentPoint.value.x,
      center_y_img: currentPoint.value.y,
      zoom_size: zoomSize.value,
      colormap: colormap.value,
      contrast_min: contrastMin.value,
      contrast_max: contrastMax.value,
      wavelength: params.value.wavelength,
      pixel_size_x: params.value.pixel_size_x,
      pixel_size_y: params.value.pixel_size_y,
      beam_center_x: params.value.center_x,
      beam_center_y: params.value.center_y,
      distance: params.value.distance,
    })
    zoomB64.value = data.zoom_b64
    currentPoint.value = { x: data.x, y: data.y, intensity: data.intensity, q: data.q, psi_rad: data.psi_rad, psi_deg: data.psi_deg }
    emit('status', `Selected: (${data.x}, ${data.y}) q=${data.q.toFixed(5)}`)
    runIntegration()
  } catch(err) { window.$toast?.(err.response?.data?.detail || err.message, true) }
}

async function runIntegration() {
  if (!sessionId.value || !currentPoint.value) return
  try {
    const { data } = await rawApi.integrate({
      session_id: sessionId.value,
      image_x: currentPoint.value.x,
      image_y: currentPoint.value.y,
      current_q: currentPoint.value.q,
      current_psi: currentPoint.value.psi_deg,
      threshold_min: threshMin.value,
      threshold_max: threshMax.value,
      ...intP.value,
      ...params.value,
    })
    intData.value = data
    selectedQ.value  = null
    selectedPsi.value = null
    await nextTick()
    drawCharts(data)
  } catch(err) {
    console.warn('Integration:', err.response?.data?.detail || err.message)
    window.$toast?.(err.response?.data?.detail || err.message, true)
  }
}

// ─── Chart helpers ────────────────────────────────────────────────────────────

function _destroyCharts() {
  import('plotly.js-dist-min').then(Plotly => {
    if (_chartQInited && chartQ.value) { Plotly.purge(chartQ.value); _chartQInited = false }
    if (_chartPsiInited && chartPsi.value) { Plotly.purge(chartPsi.value); _chartPsiInited = false }
  }).catch(() => {})
}

// BUG FIX: shared layout that DISABLES all pan/zoom/select interactions.
// dragmode: false turns off built-in drag behaviours so mouse clicks fall
// through to our plotly_click handler without accidentally panning/zooming.
function _chartLayout(title, xTitle, yTitle) {
  return {
    margin: { t: 28, b: 36, l: 48, r: 8 },
    height: 200,
    title: { text: title, font: { size: 12 } },
    xaxis: { title: xTitle, titlefont: { size: 10 }, fixedrange: true },
    yaxis: { title: yTitle, titlefont: { size: 10 }, fixedrange: true },
    showlegend: false,
    // BUG FIX: set dragmode to false so no pan/zoom/lasso is active;
    // this means mouse events go straight to plotly_click
    dragmode: false,
    hovermode: 'closest',
  }
}

// BUG FIX: config object passed to Plotly.react / newPlot.
// scrollZoom and doubleClickZoom disabled so the chart is purely for clicking.
const _plotConfig = {
  responsive: true,
  displayModeBar: false,
  scrollZoom: false,
  doubleClick: false,
  staticPlot: false,   // keep false so plotly_click still fires
}

function drawCharts(d) {
  import('plotly.js-dist-min').then(Plotly => {
    // ── q-I chart ──────────────────────────────────────────────────────────
    const iQFiltered = (d.i_q || []).map(v => v ?? null)
    const iQValid = iQFiltered.filter(v => v !== null)
    const qMin = iQValid.length ? Math.min(...iQValid) : 0
    const qMax = iQValid.length ? Math.max(...iQValid) : 1

    const qTrace = {
      x: d.q_values, y: iQFiltered,
      mode: 'lines+markers',
      line: { color: '#2499f8', width: 2 },
      marker: { size: 5, color: '#2499f8', opacity: 0.7 },
      name: 'I(q)',
      connectgaps: false,
    }
    const qRefLine = {
      x: [d.current_q, d.current_q], y: [qMin, qMax],
      mode: 'lines', line: { color: 'red', dash: 'dash' }, name: 'Position',
    }
    const qSelTraces = selectedQ.value != null ? [{
      x: [selectedQ.value, selectedQ.value], y: [qMin, qMax],
      mode: 'lines', line: { color: 'green', width: 2 }, name: 'Selected',
    }] : []

    const qTraces = [qTrace, qRefLine, ...qSelTraces]
    if (!_chartQInited) {
      Plotly.newPlot(chartQ.value, qTraces, _chartLayout('Radial Integration', 'q (Å⁻¹)', 'Intensity'), _plotConfig)
      _chartQInited = true
      // Free-click: pick any x position on the chart, not just data markers
      _addFreeClickListener(chartQ.value, xVal => {
        selectedQ.value = xVal
        drawCharts(intData.value)
      })
    } else {
      Plotly.react(chartQ.value, qTraces, _chartLayout('Radial Integration', 'q (Å⁻¹)', 'Intensity'), _plotConfig)
    }

    // ── ψ-I chart ───────────────────────────────────────────────────────────
    const iPsiFiltered = (d.i_psi || []).map(v => v ?? null)
    const iPsiValid = iPsiFiltered.filter(v => v !== null)
    const psiMin = iPsiValid.length ? Math.min(...iPsiValid) : 0
    const psiMax = iPsiValid.length ? Math.max(...iPsiValid) : 1

    const psiTrace = {
      x: d.psi_values, y: iPsiFiltered,
      mode: 'lines+markers',
      line: { color: '#27ae60', width: 2 },
      marker: { size: 5, color: '#27ae60', opacity: 0.7 },
      name: 'I(ψ)',
      connectgaps: false,
    }
    const psiRefLine = {
      x: [d.current_psi, d.current_psi], y: [psiMin, psiMax],
      mode: 'lines', line: { color: 'red', dash: 'dash' }, name: 'Position',
    }
    const psiSelTraces = selectedPsi.value != null ? [{
      x: [selectedPsi.value, selectedPsi.value], y: [psiMin, psiMax],
      mode: 'lines', line: { color: 'green', width: 2 }, name: 'Selected',
    }] : []

    const psiTraces = [psiTrace, psiRefLine, ...psiSelTraces]
    if (!_chartPsiInited) {
      Plotly.newPlot(chartPsi.value, psiTraces, _chartLayout('Azimuthal Integration', 'ψ (°)', 'Intensity'), _plotConfig)
      _chartPsiInited = true
      // Free-click: pick any x position on the chart, not just data markers
      _addFreeClickListener(chartPsi.value, xVal => {
        selectedPsi.value = xVal
        drawCharts(intData.value)
      })
    } else {
      Plotly.react(chartPsi.value, psiTraces, _chartLayout('Azimuthal Integration', 'ψ (°)', 'Intensity'), _plotConfig)
    }
  })
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

async function calcNewPixel() {
  if (!sessionId.value || !currentPoint.value) return
  try {
    const { data } = await rawApi.calcPixel({
      session_id: sessionId.value,
      selected_q: selectedQ.value,
      selected_psi: selectedPsi.value,
      current_q: currentPoint.value.q,
      current_psi: currentPoint.value.psi_deg,
      ...params.value,
    })
    // Update currentPoint with the refined position
    currentPoint.value = { x: data.x, y: data.y, intensity: data.intensity, q: data.q, psi_rad: data.psi_rad, psi_deg: data.psi_deg }
    selectedQ.value = null
    selectedPsi.value = null

    // Auto-record the refined point so it appears as a marker on the image
    const rec = await rawApi.recordPoint({
      session_id: sessionId.value,
      x: data.x, y: data.y,
      intensity: data.intensity,
      q: data.q,
      psi_rad: data.psi_rad,
    })
    records.value = rec.data.records
    window.$toast?.(`Refined & recorded point ${records.value.length}: (${data.x}, ${data.y}) q=${data.q.toFixed(5)}`)
    emit('status', `Refined: (${data.x}, ${data.y}) q=${data.q.toFixed(5)} ψ=${data.psi_deg.toFixed(2)}°`)

    // Re-run integration at the refined position so charts update
    await runIntegration()
  } catch(err) { window.$toast?.(err.response?.data?.detail || err.message, true) }
}

async function recordPoint() {
  if (!sessionId.value || !currentPoint.value) return
  try {
    const cp = currentPoint.value
    const { data } = await rawApi.recordPoint({
      session_id: sessionId.value,
      x: cp.x, y: cp.y,
      intensity: cp.intensity,
      q: cp.q,
      psi_rad: cp.psi_rad,
    })
    records.value = data.records
    window.$toast?.(`Recorded point ${records.value.length}`)
  } catch(err) { window.$toast?.(err.response?.data?.detail || err.message, true) }
}

async function deleteRecord(idx) {
  if (!sessionId.value) return
  const { data } = await rawApi.deleteRecord({ session_id: sessionId.value, index: idx })
  records.value = data.records
}

async function clearRecords() {
  if (!sessionId.value) return
  await rawApi.clearRecords(sessionId.value)
  records.value = []
}

async function handleSaveRecords() {
  if (!sessionId.value) {
    const message = '请先载入原始图，再保存提取记录。'
    setSaveFeedback('warning', message)
    window.$toast?.(message, true)
    return
  }
  if (!records.value.length) {
    const message = '当前没有可保存的提取记录。'
    setSaveFeedback('warning', message)
    window.$toast?.(message, true)
    return
  }

  const name = saveRecordName.value.trim()
  const sameNameRecord = findSameNameRecord(name)
  if (sameNameRecord) {
    const confirmed = await requestOverwriteConfirmation(sameNameRecord, name)
    if (!confirmed) {
      setSaveFeedback('info', `已取消保存“${sameNameRecord.name}”的新版本。`)
      return
    }
  }

  isSavingRecords.value = true
  try {
    const { data } = await rawApi.saveRecords({ session_id: sessionId.value, name })
    const savedRecord = data.saved_record
    await fetchSavedRecords({ quiet: true })
    saveRecordName.value = savedRecord?.name || name
    setSaveFeedback('success', `已保存“${savedRecord?.name || '未命名记录集'}”，共 ${savedRecord?.record_count ?? records.value.length} 条记录。`)
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
    const message = '请先载入原始图，再加载已保存记录。'
    setSaveFeedback('warning', message)
    window.$toast?.(message, true)
    return
  }

  loadingRecordId.value = item.id
  try {
    const { data } = await rawApi.loadRecords({ session_id: sessionId.value, record_id: item.id })
    records.value = Array.isArray(data.records) ? data.records : []
    saveRecordName.value = item.name || saveRecordName.value
    rtab.value = 'records'
    const loaded = data.loaded_record || item
    setSaveFeedback('success', `已加载“${loaded.name || item.name}”，共 ${loaded.record_count ?? records.value.length} 条记录。`)
    emit('status', `Loaded saved raw records: ${loaded.name || item.name}`)
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

// Clean up Plotly instances when component is unmounted to avoid memory leaks
onUnmounted(() => {
  _destroyCharts()
})
</script>

<style scoped>
.raw-view {
  height: 100%;
}

.content-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  height: 100%;
}

.left-panel, .right-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.left-panel {
  flex: 1;
  align-items: stretch;
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
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.section-title-stack {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
}

.section-title-subline {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-secondary);
}

.image-canvas-wrapper {
  height: 100%;
  border-radius: var(--radius-md);
  overflow: hidden;
}

.raw-image-section {
  flex: 0 0 auto;
  min-height: 0;
  display: flex;
  flex-direction: column;
  width: min(100%, 680px);
  align-self: center;
}

.raw-image-section .section-header {
  flex: 0 0 auto;
}

.raw-image-section .image-canvas-wrapper {
  flex: 0 0 auto;
  min-height: 0;
  height: auto;
}

.integrate-qi-section {
  width: min(100%, 680px);
  align-self: center;
}

.contrast-num {
  width: 80px;
  text-align: center;
  padding: 4px 6px;
  font-size: 0.8125rem;
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
  min-width: 60px;
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

.btn-group.compact {
  margin-top: 10px;
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

.form-grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.form-grid-3 {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
}

.instrument-params-grid {
  gap: 12px;
}

.form-field-stack {
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 6px;
  min-width: 0;
}

.form-field-stack label {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.form-field-stack input {
  width: 100%;
}

.input-small {
  width: 100%;
  padding: 6px 8px;
  font-size: 0.8125rem;
}

.zoom-container {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.zoom-image {
  flex: 0 0 180px;
  background: #111;
  border-radius: var(--radius-md);
  overflow: hidden;
}

.zoom-image img {
  width: 180px;
  cursor: crosshair;
  display: block;
}

.zoom-placeholder {
  width: 180px;
  height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
  font-size: 0.8125rem;
}

.zoom-info {
  flex: 1;
  font-size: 0.8125rem;
  line-height: 1.8;
}

.point-info .label {
  color: var(--text-secondary);
}

.selection-info {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 12px;
  font-size: 0.8125rem;
}

/* BUG FIX: cursor hint above charts */
.chart-hint {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin: 0 0 4px 0;
}

.chart-container {
  margin-top: 8px;
  /* Prevent Plotly's internal drag cursor from leaking out */
  cursor: crosshair;
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

.dimmed {
  opacity: 0.5;
  color: var(--text-muted);
  font-size: 0.875rem;
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
  align-items: center;
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
