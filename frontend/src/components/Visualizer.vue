<template>
  <div class="visualizer" :class="{ 'compact-mode': compact }">
    <div class="top-bar">
      <span class="title">{{ t('visualizer.dataSource') }}：</span>
      <div class="source-group">
        <label>
          <input type="radio" v-model="activePanel" value="raw" />
          <span>{{ t('visualizer.rawImage') }} (.tif / .edf / .cbf)</span>
        </label>
        <label>
          <input type="radio" v-model="activePanel" value="int" />
          <span>{{ t('visualizer.integration2D') }} (.npy / .tif)</span>
        </label>
      </div>
      <span class="spacer"></span>
      <span class="backend-status">
        pyFAI: {{ status.pyfai ? '✓' : '✗' }}&nbsp;&nbsp;
        fabio: {{ status.fabio ? '✓' : '✗' }}
      </span>
    </div>

    <div class="main-content">
      <template v-if="activePanel === 'raw'">
        <div class="sidebar">
          <div class="group-box">
            <span class="group-title">{{ t('visualizer.fileImport') }}</span>
            <div class="inner">
              <button class="btn" @click="triggerUpload('rawImage')">
                ① {{ t('visualizer.importDiffractionImage') }}&nbsp;(.tif / .edf / .cbf)
              </button>
              <button class="btn" :disabled="!raw.imageLoaded" @click="triggerUpload('rawPoni')">
                ② {{ t('visualizer.importPoniFile') }}
              </button>
              <div v-if="!compact" class="btn-row">
                <button class="btn btn-cyan" :disabled="!raw.imageLoaded"
                        @click="triggerUpload('rawFullMiller')">
                  {{ t('visualizer.importFullMiller') }} ■
                </button>
                <button class="btn btn-orange" :disabled="!raw.imageLoaded"
                        @click="triggerUpload('rawOutputMiller')">
                  {{ t('visualizer.importOutputMiller') }} ◆
                </button>
              </div>
              <div class="stat-labels">
                <span class="lbl-full">{{ t('visualizer.fullMiller') }}: {{ raw.fullCount > 0 ? raw.fullCount + ' ' + t('visualizer.points') : t('visualizer.notLoaded') }}</span>
                <span class="lbl-output">{{ t('visualizer.outputMiller') }}: {{ raw.outputCount > 0 ? raw.outputCount + ' ' + t('visualizer.points') : t('visualizer.notLoaded') }}</span>
              </div>
              <div class="btn-row">
                <button class="btn" :disabled="!raw.imageLoaded" @click="saveRawImage">{{ t('visualizer.saveMarkedImage') }}</button>
                <button class="btn" :disabled="!raw.imageLoaded" @click="clearRawMiller">{{ t('visualizer.clearAllMarkers') }}</button>
              </div>
            </div>
          </div>

          <div class="group-box">
            <span class="group-title">{{ t('visualizer.instrumentParams') }}</span>
            <div class="inner">
              <div class="form-row">
                <label>{{ t('visualizer.poniStatus') }}:</label>
                <span class="poni-status" :class="raw.poniLoaded ? 'poni-ok' : 'poni-no'">
                  {{ raw.poniLoaded ? '✓ ' + t('visualizer.loaded') : t('visualizer.notLoaded') }}
                </span>
              </div>
              <div class="form-row">
                <label>{{ t('visualizer.wavelength') }} (Å):</label>
                <input type="number" v-model.number="raw.p.wl" step="0.0001" min="0" @change="applyRawParams" />
              </div>
              <div class="form-row">
                <label>{{ t('visualizer.pixelX') }} (μm):</label>
                <input type="number" v-model.number="raw.p.px" step="1" min="0" @change="applyRawParams" />
              </div>
              <div class="form-row">
                <label>{{ t('visualizer.pixelY') }} (μm):</label>
                <input type="number" v-model.number="raw.p.py" step="1" min="0" @change="applyRawParams" />
              </div>
              <div class="form-row">
                <label>{{ t('visualizer.centerX') }} (px):</label>
                <input type="number" v-model.number="raw.p.cx" step="1" @change="applyRawParams" />
              </div>
              <div class="form-row">
                <label>{{ t('visualizer.centerY') }} (px):</label>
                <input type="number" v-model.number="raw.p.cy" step="1" @change="applyRawParams" />
              </div>
              <div class="form-row">
                <label>{{ t('visualizer.distance') }} (mm):</label>
                <input type="number" v-model.number="raw.p.dist" step="1" min="0" @change="applyRawParams" />
              </div>
              <div class="form-row">
                <label>{{ t('visualizer.psiRotationOffset') }} (°):</label>
                <input type="number" v-model.number="raw.p.rot" step="0.5" @change="applyRawParams" />
              </div>
              <button class="btn" :disabled="!raw.imageLoaded" @click="renderRaw">
                ⟳ {{ t('visualizer.applyParamsAndRedraw') }}
              </button>
            </div>
          </div>

          <div class="group-box">
            <span class="group-title">{{ t('visualizer.contrastAndDisplay') }}</span>
            <div class="inner">
              <div class="form-row">
                <label>{{ t('visualizer.mode') }}:</label>
                <select v-model="raw.p.mode" @change="renderRaw">
                  <option value="Linear">Linear</option>
                  <option value="Log">Log</option>
                </select>
                <label>{{ t('visualizer.color') }}:</label>
                <select v-model="raw.p.colormap" @change="renderRaw">
                  <option value="灰度">{{ t('visualizer.cmapGray') }}</option>
                  <option value="反转灰度">{{ t('visualizer.cmapGrayR') }}</option>
                  <option value="热力图">{{ t('visualizer.cmapHot') }}</option>
                  <option value="彩虹">{{ t('visualizer.cmapJet') }}</option>
                </select>
              </div>
              <div class="slider-row">
                <label>Min:</label>
                <input type="range" :min="raw.imgMin" :max="raw.imgMax"
                       v-model.number="raw.p.cmin" @input="debounceRenderRaw" />
                <input type="number" :min="raw.imgMin" :max="raw.imgMax"
                       v-model.number="raw.p.cmin" @change="renderRaw" />
              </div>
              <div class="slider-row">
                <label>Max:</label>
                <input type="range" :min="raw.imgMin" :max="raw.imgMax"
                       v-model.number="raw.p.cmax" @input="debounceRenderRaw" />
                <input type="number" :min="raw.imgMin" :max="raw.imgMax"
                       v-model.number="raw.p.cmax" @change="renderRaw" />
              </div>
            </div>
          </div>

          <div class="group-box">
            <span class="group-title">{{ t('visualizer.displayControl') }}</span>
            <div class="inner">
              <button class="btn btn-green" @click="refreshRawView">
                ⟳ {{ t('visualizer.refreshView') }}
              </button>
              <button class="btn" @click="resetZoom('raw')">{{ t('visualizer.resetZoom') }}</button>
              <label class="check-row">
                <input type="checkbox" v-model="raw.p.showLabels" @change="renderRaw" />
                {{ t('visualizer.showMillerLabels') }}
              </label>
              <div class="form-row">
                <label>{{ t('visualizer.quadrant') }}:</label>
                <select v-model="raw.p.quadrant" @change="renderRaw">
                  <option value="第一象限">{{ t('visualizer.quadI') }}</option>
                  <option value="第二象限">{{ t('visualizer.quadII') }}</option>
                  <option value="第三象限">{{ t('visualizer.quadIII') }}</option>
                  <option value="第四象限">{{ t('visualizer.quadIV') }}</option>
                </select>
              </div>
              <div class="legend-row">
                <span class="leg-cyan">■&nbsp;{{ t('visualizer.fullMiller') }}</span>
                <span class="leg-orange">◆&nbsp;{{ t('visualizer.outputMiller') }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="right-panel">
          <div class="image-toolbar">
            <span>{{ t('visualizer.zoom') }}:&nbsp;<span class="zoom-info">{{ (raw.zoom * 100).toFixed(0) }}%</span></span>
            <button class="btn" @click="resetZoom('raw')">{{ t('visualizer.fitWindow') }}</button>
            <button class="btn" @click="raw.zoom *= 2; clampZoom('raw')">{{ t('visualizer.zoomIn2x') }}</button>
            <button class="btn" @click="raw.zoom /= 2; clampZoom('raw')">{{ t('visualizer.zoomOut') }}</button>
            <span v-if="raw.imageLoaded" class="image-size-info">
              {{ raw.imgW }}×{{ raw.imgH }} px
            </span>
          </div>
          <div class="image-area" ref="rawCanvas"
               @mousedown.prevent="startDrag($event,'raw')"
               @mousemove="onDrag($event,'raw')"
               @mouseup="stopDrag"
               @mouseleave="stopDrag"
               @wheel.prevent="onWheel($event,'raw')">
            <div class="loading-overlay" v-if="loading">
              <div class="spinner"></div>{{ t('visualizer.loading') }}…
            </div>
            <img v-if="raw.imageSrc" :src="'data:image/png;base64,' + raw.imageSrc"
                 :style="rawImgStyle" draggable="false" />
            <div class="placeholder-text" v-else>
              {{ t('visualizer.pleaseImportDiffractionImage') }}<br/>
              (.tif / .edf / .cbf)
            </div>
          </div>
        </div>
      </template>

      <template v-else-if="activePanel === 'int'">
        <div class="sidebar">
          <div class="group-box">
            <span class="group-title">{{ t('visualizer.fileImport') }}</span>
            <div class="inner">
              <button class="btn" @click="triggerUpload('intImage')">
                ① {{ t('visualizer.import2DIntegrationImage') }}&nbsp;(.npy / .tif)
              </button>
              <button class="btn" :disabled="!int2d.imageLoaded" @click="triggerUpload('intInfo')">
                ② {{ t('visualizer.importCoordinateInfoFile') }}
              </button>
              <button class="btn btn-green" :disabled="!int2d.imageLoaded" @click="renderInt">
                ⟳ {{ t('visualizer.refreshImage') }}
              </button>
              <div v-if="!compact" class="btn-row">
                <button class="btn btn-cyan" :disabled="!int2d.imageLoaded"
                        @click="triggerUpload('intFullMiller')">
                  {{ t('visualizer.importFullMiller') }} ●
                </button>
                <button class="btn btn-orange" :disabled="!int2d.imageLoaded"
                        @click="triggerUpload('intOutputMiller')">
                  {{ t('visualizer.importOutputMiller') }} ◆
                </button>
              </div>
              <div class="stat-labels">
                <span class="lbl-full">{{ t('visualizer.fullMiller') }}: {{ int2d.fullCount > 0 ? int2d.fullCount + ' ' + t('visualizer.points') : t('visualizer.notLoaded') }}</span>
                <span class="lbl-output">{{ t('visualizer.outputMiller') }}: {{ int2d.outputCount > 0 ? int2d.outputCount + ' ' + t('visualizer.points') : t('visualizer.notLoaded') }}</span>
              </div>
              <div class="btn-row">
                <button class="btn" :disabled="!int2d.imageLoaded" @click="saveIntImage">{{ t('visualizer.saveMarkedImage') }}</button>
                <button class="btn" :disabled="!int2d.imageLoaded" @click="clearIntMiller">{{ t('visualizer.clearMarkers') }}</button>
              </div>
            </div>
          </div>

          <div class="group-box">
            <span class="group-title">{{ t('visualizer.coordinateRange') }}</span>
            <div class="inner">
              <div class="form-row">
                <label>q Min (Å⁻¹):</label>
                <input type="number" v-model.number="int2d.p.qMin" step="0.01" />
              </div>
              <div class="form-row">
                <label>q Max (Å⁻¹):</label>
                <input type="number" v-model.number="int2d.p.qMax" step="0.01" />
              </div>
              <div class="form-row">
                <label>{{ t('visualizer.azimuthMin') }} (°):</label>
                <input type="number" v-model.number="int2d.p.azMin" step="1" />
              </div>
              <div class="form-row">
                <label>{{ t('visualizer.azimuthMax') }} (°):</label>
                <input type="number" v-model.number="int2d.p.azMax" step="1" />
              </div>
              <button class="btn" :disabled="!int2d.imageLoaded" @click="applyIntRanges">
                {{ t('visualizer.applyCoordinateRange') }}
              </button>
            </div>
          </div>

          <div class="group-box">
            <span class="group-title">{{ t('visualizer.contrastAndColor') }}</span>
            <div class="inner">
              <div class="form-row">
                <label>{{ t('visualizer.color') }}:</label>
                <select v-model="int2d.p.colormap" @change="renderInt">
                  <option value="灰度">{{ t('visualizer.cmapGray') }}</option>
                  <option value="反转灰度">{{ t('visualizer.cmapGrayR') }}</option>
                  <option value="热力图">{{ t('visualizer.cmapHot') }}</option>
                  <option value="彩虹">{{ t('visualizer.cmapJet') }}</option>
                </select>
                <label>{{ t('visualizer.mode') }}:</label>
                <select v-model="int2d.p.mode" @change="renderInt">
                  <option value="Linear">Linear</option>
                  <option value="Log">Log</option>
                </select>
              </div>
              <div class="slider-row">
                <label>Min:</label>
                <input type="range" :min="int2d.imgMin" :max="int2d.imgMax"
                       v-model.number="int2d.p.cmin" @input="debounceRenderInt" />
                <input type="number" :min="int2d.imgMin" :max="int2d.imgMax"
                       v-model.number="int2d.p.cmin" @change="renderInt" />
              </div>
              <div class="slider-row">
                <label>Max:</label>
                <input type="range" :min="int2d.imgMin" :max="int2d.imgMax"
                       v-model.number="int2d.p.cmax" @input="debounceRenderInt" />
                <input type="number" :min="int2d.imgMin" :max="int2d.imgMax"
                       v-model.number="int2d.p.cmax" @change="renderInt" />
              </div>
            </div>
          </div>

          <div class="group-box">
            <span class="group-title">{{ t('visualizer.millerCoordinateMapping') }}</span>
            <div class="inner">
              <div class="form-row">
                <label>{{ t('visualizer.psiConvention') }}:</label>
                <select v-model="int2d.p.convention" @change="renderInt">
                  <option value="ccw">{{ t('visualizer.psiConventionCCW') }}</option>
                  <option value="cw">{{ t('visualizer.psiConventionCW') }}</option>
                </select>
              </div>
              <div class="form-row">
                <label>{{ t('visualizer.psi0CorrespondingAz') }} (°):</label>
                <input type="number" v-model.number="int2d.p.psiOffset" step="1"
                       @change="renderInt" />
              </div>
              <div class="legend-row">
                <span class="leg-cyan">●&nbsp;{{ t('visualizer.fullMillerCyan') }}</span>
                <span class="leg-orange">◆&nbsp;{{ t('visualizer.outputMillerOrange') }}</span>
              </div>
            </div>
          </div>

          <div class="group-box">
            <span class="group-title">{{ t('visualizer.azimuthCropDisplay') }}</span>
            <div class="inner">
              <label class="check-row">
                <input type="checkbox" v-model="int2d.p.azCropEnabled" @change="renderInt" />
                {{ t('visualizer.enableCrop') }}
              </label>
              <div class="form-row">
                <label>{{ t('visualizer.from') }} (°):</label>
                <input type="number" v-model.number="int2d.p.azCropMin" step="5"
                       :disabled="!int2d.p.azCropEnabled" @change="renderInt" />
              </div>
              <div class="form-row">
                <label>{{ t('visualizer.to') }} (°):</label>
                <input type="number" v-model.number="int2d.p.azCropMax" step="5"
                       :disabled="!int2d.p.azCropEnabled" @change="renderInt" />
              </div>
            </div>
          </div>
        </div>

        <div class="right-panel">
          <div class="image-toolbar">
            <span>{{ t('visualizer.zoom') }}:&nbsp;<span class="zoom-info">{{ (int2d.zoom * 100).toFixed(0) }}%</span></span>
            <button class="btn" @click="resetZoom('int')">{{ t('visualizer.fitWindow') }}</button>
            <button class="btn" @click="int2d.zoom *= 1.5; clampZoom('int')">{{ t('visualizer.zoomIn') }}</button>
            <button class="btn" @click="int2d.zoom /= 1.5; clampZoom('int')">{{ t('visualizer.zoomOut') }}</button>
          </div>
          <div class="image-area" ref="intCanvas"
               @mousedown.prevent="startDrag($event,'int')"
               @mousemove="onDrag($event,'int')"
               @mouseup="stopDrag"
               @mouseleave="stopDrag"
               @wheel.prevent="onWheel($event,'int')">
            <div class="loading-overlay" v-if="loading">
              <div class="spinner"></div>{{ t('visualizer.rendering') }}…
            </div>
            <img v-if="int2d.imageSrc" :src="'data:image/png;base64,' + int2d.imageSrc"
                 :style="intImgStyle" draggable="false" />
            <div class="placeholder-text" v-else>
              {{ t('visualizer.pleaseImport2DIntegrationImage') }}<br/>
              (.npy / .tif)
            </div>
          </div>
        </div>
      </template>
    </div>

    <div class="status-bar">{{ statusMsg }}</div>

    <input ref="fileRawImage"    type="file" accept=".tif,.tiff,.edf,.cbf,.img" style="display:none" @change="e=>onFileChange(e,'rawImage')" />
    <input ref="fileRawPoni"     type="file" accept=".poni" style="display:none" @change="e=>onFileChange(e,'rawPoni')" />
    <input ref="fileRawFull"     type="file" accept=".txt" style="display:none" @change="e=>onFileChange(e,'rawFullMiller')" />
    <input ref="fileRawOutput"   type="file" accept=".txt" style="display:none" @change="e=>onFileChange(e,'rawOutputMiller')" />
    <input ref="fileIntImage"    type="file" accept=".npy,.tif,.tiff" style="display:none" @change="e=>onFileChange(e,'intImage')" />
    <input ref="fileIntInfo"     type="file" accept=".txt" style="display:none" @change="e=>onFileChange(e,'intInfo')" />
    <input ref="fileIntFull"     type="file" accept=".txt" style="display:none" @change="e=>onFileChange(e,'intFullMiller')" />
    <input ref="fileIntOutput"   type="file" accept=".txt" style="display:none" @change="e=>onFileChange(e,'intOutputMiller')" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import axios from 'axios'

const emit = defineEmits(['raw-session-ready'])

const props = defineProps({
  workDir: {
    type: String,
    default: '',
  },
  resultType: {
    type: String,
    default: 'indexing',
  },
  millerData: {
    type: Array,
    default: null,
  },
  overlayGroups: {
    type: Array,
    default: null,
  },
  importRequestKey: {
    type: Number,
    default: 0,
  },
  compact: {
    type: Boolean,
    default: false,
  },
})

const { t } = useI18n()

const API_BASE = '/api/visualizer'

const activePanel = ref('raw')
const statusMsg = ref('')
const loading = ref(false)
const status = reactive({ fabio: false, pyfai: false })

const drag = reactive({ active: false, lastX: 0, lastY: 0, panel: '' })

let rawDebTimer = null
let intDebTimer = null
const EXPORT_COLORMAP = '灰度'

const raw = reactive({
  imageLoaded: false,
  imageSrc: '',
  imgW: 0, imgH: 0,
  imgMin: 0, imgMax: 65535,
  poniLoaded: false,
  fullCount: 0,
  outputCount: 0,
  zoom: 1.0,
  panX: 0, panY: 0,
  p: {
    wl: 1.0, px: 100, py: 100, cx: 0, cy: 0, dist: 1000, rot: 0.0,
    quadrant: '第一象限', mode: 'Linear', colormap: '灰度',
    cmin: 0, cmax: 65535, showLabels: true,
  },
})

const int2d = reactive({
  imageLoaded: false,
  imageSrc: '',
  imgMin: 0, imgMax: 65535,
  fullCount: 0,
  outputCount: 0,
  zoom: 1.0,
  panX: 0, panY: 0,
  p: {
    qMin: 0.0, qMax: 1.0, azMin: -180.0, azMax: 180.0,
    colormap: '灰度', mode: 'Linear', cmin: 0, cmax: 65535,
    convention: 'ccw', psiOffset: 0.0,
    azCropEnabled: false, azCropMin: -10.0, azCropMax: 120.0,
  },
})

const rawCanvas = ref(null)
const intCanvas = ref(null)
const fileRawImage = ref(null)
const fileRawPoni = ref(null)
const fileRawFull = ref(null)
const fileRawOutput = ref(null)
const fileIntImage = ref(null)
const fileIntInfo = ref(null)
const fileIntFull = ref(null)
const fileIntOutput = ref(null)

const rawImgStyle = computed(() => ({
  transform: `translate(${raw.panX}px, ${raw.panY}px) scale(${raw.zoom})`,
  transformOrigin: '0 0',
}))

const intImgStyle = computed(() => ({
  transform: `translate(${int2d.panX}px, ${int2d.panY}px) scale(${int2d.zoom})`,
  transformOrigin: '0 0',
}))

function setStatus(msg) { statusMsg.value = msg }

function clampZoom(panel) {
  const s = panel === 'raw' ? raw : int2d
  s.zoom = Math.max(0.02, Math.min(s.zoom, 50))
}

function resetZoom(panel) {
  const s = panel === 'raw' ? raw : int2d
  const container = panel === 'raw' ? rawCanvas.value : intCanvas.value
  if (!container) return
  const cw = container.clientWidth, ch = container.clientHeight
  const iw = panel === 'raw' ? (raw.imgW || cw) : cw
  const ih = panel === 'raw' ? (raw.imgH || ch) : ch
  const scaleX = cw / iw, scaleY = ch / ih
  s.zoom = Math.min(scaleX, scaleY, 1.0)
  s.panX = (cw - iw * s.zoom) / 2
  s.panY = (ch - ih * s.zoom) / 2
}

function startDrag(e, panel) {
  drag.active = true
  drag.panel = panel
  drag.lastX = e.clientX
  drag.lastY = e.clientY
}

function onDrag(e, panel) {
  if (!drag.active || drag.panel !== panel) return
  const dx = e.clientX - drag.lastX, dy = e.clientY - drag.lastY
  drag.lastX = e.clientX
  drag.lastY = e.clientY
  const s = panel === 'raw' ? raw : int2d
  s.panX += dx
  s.panY += dy
}

function stopDrag() { drag.active = false }

function onWheel(e, panel) {
  const s = panel === 'raw' ? raw : int2d
  const container = panel === 'raw' ? rawCanvas.value : intCanvas.value
  if (!container) return
  const rect = container.getBoundingClientRect()
  const mx = e.clientX - rect.left, my = e.clientY - rect.top
  const oldZoom = s.zoom
  const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12
  s.zoom = Math.max(0.02, Math.min(oldZoom * factor, 50))
  s.panX = mx - (mx - s.panX) * (s.zoom / oldZoom)
  s.panY = my - (my - s.panY) * (s.zoom / oldZoom)
}

const refMap = {
  rawImage: () => fileRawImage.value,
  rawPoni: () => fileRawPoni.value,
  rawFullMiller: () => fileRawFull.value,
  rawOutputMiller: () => fileRawOutput.value,
  intImage: () => fileIntImage.value,
  intInfo: () => fileIntInfo.value,
  intFullMiller: () => fileIntFull.value,
  intOutputMiller: () => fileIntOutput.value,
}

function triggerUpload(key) {
  const el = refMap[key]?.()
  if (el) { el.value = ''; el.click() }
}

async function onFileChange(e, key) {
  const file = e.target.files[0]
  if (!file) return
  loading.value = true
  try {
    switch (key) {
      case 'rawImage': await uploadRawImage(file); break
      case 'rawPoni': await uploadRawPoni(file); break
      case 'rawFullMiller': await uploadRawMiller(file, 'full'); break
      case 'rawOutputMiller': await uploadRawMiller(file, 'output'); break
      case 'intImage': await uploadIntImage(file); break
      case 'intInfo': await uploadIntInfo(file); break
      case 'intFullMiller': await uploadIntMiller(file, 'full'); break
      case 'intOutputMiller': await uploadIntMiller(file, 'output'); break
    }
  } catch(err) {
    setStatus('Error: ' + (err.response?.data?.detail || err.message))
  } finally {
    loading.value = false
  }
}

async function uploadRawImage(file) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await axios.post(`${API_BASE}/raw/upload-image`, fd)
  raw.imageLoaded = true
  raw.imgW = data.width
  raw.imgH = data.height
  raw.imgMin = Math.floor(data.min)
  raw.imgMax = Math.ceil(data.max)
  raw.p.cmin = Math.floor(data.p01 ?? data.min)
  raw.p.cmax = Math.ceil(data.p99 ?? data.max)
  raw.fullCount = 0
  raw.outputCount = 0
  raw.poniLoaded = false
  setStatus(data.message)
  await renderRaw()
  await nextTick()
  resetZoom('raw')
  emit('raw-session-ready')
}

async function uploadRawPoni(file) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await axios.post(`${API_BASE}/raw/upload-poni`, fd)
  raw.poniLoaded = true
  raw.p.wl = data.wl
  raw.p.px = data.px
  raw.p.py = data.py
  raw.p.cx = data.cx
  raw.p.cy = data.cy
  raw.p.dist = data.dist
  setStatus(data.message)
  await renderRaw()
}

async function uploadRawMiller(file, type) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await axios.post(`${API_BASE}/raw/upload-miller?miller_type=${type}`, fd)
  if (type === 'full') raw.fullCount = data.count
  else raw.outputCount = data.count
  setStatus(data.message)
  await renderRaw()
}

async function clearRawMiller() {
  await axios.delete(`${API_BASE}/raw/miller?miller_type=all`)
  raw.fullCount = 0
  raw.outputCount = 0
  setStatus('All Miller markers cleared')
  await renderRaw()
}

async function renderRaw() {
  if (!raw.imageLoaded) return
  loading.value = true
  try {
    const { data } = await axios.post(`${API_BASE}/raw/render`, {
      contrast_min: raw.p.cmin,
      contrast_max: raw.p.cmax,
      mode: raw.p.mode,
      colormap: raw.p.colormap,
      show_labels: raw.p.showLabels,
      quadrant: raw.p.quadrant,
      rot_offset: parseFloat(raw.p.rot) || 0,
      wl: parseFloat(raw.p.wl) || 1,
      px: parseFloat(raw.p.px) || 100,
      py: parseFloat(raw.p.py) || 100,
      cx: parseFloat(raw.p.cx) || 0,
      cy: parseFloat(raw.p.cy) || 0,
      dist: parseFloat(raw.p.dist) || 1000,
      use_pyfai: true,
    })
    raw.imageSrc = data.image
    const msg = `Rendered | FullMiller: ${data.full_miller_count} pts | outputMiller: ${data.output_miller_count} pts${data.pyfai_used ? ' | pyFAI ✓' : ' | Manual geometry'}`
    setStatus(msg)
  } finally {
    loading.value = false
  }
}

async function applyRawParams() {
  await renderRaw()
}

async function refreshRawView() {
  await renderRaw()
  await nextTick()
  resetZoom('raw')
  setStatus('View refreshed, Miller points recalculated and centered')
}

function debounceRenderRaw() {
  clearTimeout(rawDebTimer)
  rawDebTimer = setTimeout(renderRaw, 300)
}

function downloadBase64Image(imageSrc, filename) {
  const a = document.createElement('a')
  a.href = 'data:image/png;base64,' + imageSrc
  a.download = filename
  a.click()
}

function getExportAdjustmentsSummary(adjustments) {
  if (!adjustments.length) return ''
  return ` | export profile: ${adjustments.join(' + ')}`
}

async function prepareRawExportImage() {
  const adjustments = []
  const hasMarkers = raw.fullCount > 0 || raw.outputCount > 0
  let needsRender = false

  if (hasMarkers && raw.p.colormap !== EXPORT_COLORMAP) {
    raw.p.colormap = EXPORT_COLORMAP
    adjustments.push('gray colormap')
    needsRender = true
  }

  if (hasMarkers && !raw.p.showLabels) {
    raw.p.showLabels = true
    adjustments.push('labels on')
    needsRender = true
  }

  if (needsRender) {
    await renderRaw()
  }

  return adjustments
}

async function saveRawImage() {
  if (!raw.imageSrc) return
  try {
    const adjustments = await prepareRawExportImage()
    downloadBase64Image(raw.imageSrc, 'diffraction_marked.png')
    setStatus(`Marked image saved${getExportAdjustmentsSummary(adjustments)}`)
  } catch(err) {
    setStatus('Error: ' + (err.response?.data?.detail || err.message))
  }
}

async function uploadIntImage(file) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await axios.post(`${API_BASE}/int/upload-image`, fd)
  int2d.imageLoaded = true
  int2d.imgMin = Math.floor(data.min)
  int2d.imgMax = Math.ceil(data.max)
  int2d.p.cmin = Math.floor(data.p01 ?? data.min)
  int2d.p.cmax = Math.ceil(data.p99 ?? data.max)
  int2d.fullCount = 0
  int2d.outputCount = 0
  setStatus(data.message)
  await renderInt()
  await nextTick()
  resetZoom('int')
}

async function uploadIntInfo(file) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await axios.post(`${API_BASE}/int/upload-info`, fd)
  int2d.p.qMin = data.q_min
  int2d.p.qMax = data.q_max
  int2d.p.azMin = data.az_min
  int2d.p.azMax = data.az_max
  setStatus(data.message)
  await renderInt()
}

async function uploadIntMiller(file, type) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await axios.post(`${API_BASE}/int/upload-miller?miller_type=${type}`, fd)
  if (type === 'full') int2d.fullCount = data.count
  else int2d.outputCount = data.count
  setStatus(data.message)
  await renderInt()
}

async function clearIntMiller() {
  await axios.delete(`${API_BASE}/int/miller?miller_type=all`)
  int2d.fullCount = 0
  int2d.outputCount = 0
  setStatus('All Miller markers cleared')
  await renderInt()
}

async function applyIntRanges() {
  try {
    await axios.put(`${API_BASE}/int/coordinate-ranges`, {
      q_min: int2d.p.qMin,
      q_max: int2d.p.qMax,
      az_min: int2d.p.azMin,
      az_max: int2d.p.azMax,
    })
    setStatus('Coordinate range updated')
    await renderInt()
  } catch(err) {
    setStatus('Error: ' + (err.response?.data?.detail || err.message))
  }
}

async function renderInt() {
  if (!int2d.imageLoaded) return
  loading.value = true
  try {
    const { data } = await axios.post(`${API_BASE}/int/render`, {
      contrast_min: int2d.p.cmin,
      contrast_max: int2d.p.cmax,
      colormap: int2d.p.colormap,
      mode: int2d.p.mode,
      convention: int2d.p.convention,
      psi_offset: int2d.p.psiOffset,
      az_crop_enabled: int2d.p.azCropEnabled,
      az_crop_min: int2d.p.azCropMin,
      az_crop_max: int2d.p.azCropMax,
    })
    int2d.imageSrc = data.image
    setStatus(`Rendered | FullMiller: ${data.full_miller_count} pts | outputMiller: ${data.output_miller_count} pts`)
  } finally {
    loading.value = false
  }
}

function debounceRenderInt() {
  clearTimeout(intDebTimer)
  intDebTimer = setTimeout(renderInt, 300)
}

async function prepareIntExportImage() {
  const adjustments = []
  const hasMarkers = int2d.fullCount > 0 || int2d.outputCount > 0

  if (hasMarkers && int2d.p.colormap !== EXPORT_COLORMAP) {
    int2d.p.colormap = EXPORT_COLORMAP
    adjustments.push('gray colormap')
    await renderInt()
  }

  return adjustments
}

async function saveIntImage() {
  if (!int2d.imageSrc) return
  try {
    const adjustments = await prepareIntExportImage()
    downloadBase64Image(int2d.imageSrc, '2d_integrated_marked.png')
    setStatus(`Marked image saved${getExportAdjustmentsSummary(adjustments)}`)
  } catch(err) {
    setStatus('Error: ' + (err.response?.data?.detail || err.message))
  }
}

onMounted(async () => {
  try {
    const { data } = await axios.get(`${API_BASE}/status`)
    status.fabio = data.fabio
    status.pyfai = data.pyfai
    setStatus(`Backend connected — pyFAI: ${data.pyfai ? '✓' : '✗'}  fabio: ${data.fabio ? '✓' : '✗'}`)
  } catch {
    setStatus('⚠ Cannot connect to backend, please confirm the backend is running')
  }
  if (props.workDir) {
    await loadFromWorkDir(props.workDir)
  }
})

async function loadFromWorkDir(dir) {
  if (!dir) return
  loading.value = true
  try {
    const { data } = await axios.post(`${API_BASE}/raw/load-workdir`, { work_dir: dir })
    if (data.image_loaded) {
      raw.imageLoaded = true
      raw.imgW = data.width || 0
      raw.imgH = data.height || 0
      raw.imgMin = Math.floor(data.min || 0)
      raw.imgMax = Math.ceil(data.max || 65535)
      raw.p.cmin = Math.floor(data.p01 ?? data.min ?? 0)
      raw.p.cmax = Math.ceil(data.p99 ?? data.max ?? 65535)
      if (data.poni) {
        raw.poniLoaded = true
        raw.p.wl = data.poni.wl || raw.p.wl
        raw.p.px = data.poni.px || raw.p.px
        raw.p.py = data.poni.py || raw.p.py
        raw.p.cx = data.poni.cx || raw.p.cx
        raw.p.cy = data.poni.cy || raw.p.cy
        raw.p.dist = data.poni.dist || raw.p.dist
      }
      if (data.full_miller_count !== undefined) raw.fullCount = data.full_miller_count
      if (data.output_miller_count !== undefined) raw.outputCount = data.output_miller_count
      await renderRaw()
      await nextTick()
      resetZoom('raw')
      setStatus(data.message || `Loaded from workDir: ${dir}`)
      emit('raw-session-ready')
    }
  } catch (err) {
    setStatus('Error loading workDir: ' + (err.response?.data?.detail || err.message))
  } finally {
    loading.value = false
  }
}

watch(() => props.workDir, async (newDir) => {
  if (newDir) {
    await loadFromWorkDir(newDir)
  }
})

async function loadOverlayGroups() {
  if (!props.overlayGroups || props.overlayGroups.length === 0) return
  if (!raw.imageLoaded) return
  loading.value = true
  try {
    const groups = props.overlayGroups.slice(0, 5).map(g => ({
      label: g.label || '',
      full_miller_content: g.fullMillerContent || '',
    }))
    const { data } = await axios.post(`${API_BASE}/raw/set-miller-content`, { groups })
    raw.fullCount = data.total_count || 0
    setStatus(data.message || `Overlay: ${groups.length} group(s) loaded`)
    await renderRaw()
  } catch (err) {
    setStatus('Error loading overlay groups: ' + (err.response?.data?.detail || err.message))
  } finally {
    loading.value = false
  }
}

watch(() => props.importRequestKey, async (newKey, oldKey) => {
  if (!newKey || newKey === oldKey) return
  if (!raw.imageLoaded) {
    setStatus('Please import a diffraction image before loading FullMiller markers')
    return
  }
  await loadOverlayGroups()
})
</script>

<style scoped>
.visualizer {
  height: calc(100vh - var(--header-height) - 48px);
  display: flex;
  flex-direction: column;
}

.top-bar {
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  padding: 0 16px;
  height: 52px;
  flex-shrink: 0;
  gap: 24px;
}

.top-bar .title {
  font-weight: 400;
  font-size: 14px;
  color: var(--text-primary);
  white-space: nowrap;
}

.source-group {
  display: flex;
  gap: 8px;
  align-items: center;
}

.source-group label {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-weight: 400;
  font-size: 13px;
  color: var(--text-primary);
  padding: 6px 14px;
  border-radius: 6px;
  transition: background .15s;
}

.source-group label:hover {
  background: var(--bg-hover);
}

.source-group label:has(input:checked) {
  background: var(--primary-bg);
}

.source-group label:has(input:checked) span {
  color: var(--primary);
}

.source-group input[type="radio"] {
  accent-color: var(--primary);
  width: 15px;
  height: 15px;
}

.top-bar .spacer {
  flex: 1;
}

.backend-status {
  font-size: 12px;
  color: var(--text-secondary);
}

.status-bar {
  background: var(--bg-surface);
  border-top: 1px solid var(--border);
  font-size: 12px;
  color: var(--text-secondary);
  padding: 3px 12px;
  flex-shrink: 0;
  min-height: 22px;
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.sidebar {
  width: 360px;
  min-width: 280px;
  max-width: 400px;
  background: var(--bg-surface);
  border-right: 1px solid var(--border);
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}

.group-box {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 10px 12px;
  background: transparent;
  position: relative;
}

.group-box .group-title {
  position: absolute;
  top: -11px;
  left: 10px;
  background: var(--bg-surface);
  padding: 0 6px;
  font-weight: 400;
  font-size: 13px;
  color: var(--text-primary);
}

.group-box .inner {
  display: flex;
  flex-direction: column;
  gap: 7px;
  margin-top: 4px;
}

.btn {
  background: var(--primary-bg);
  color: var(--primary);
  border: none;
  border-radius: 8px;
  padding: 7px 12px;
  font-weight: 400;
  font-size: 12px;
  cursor: pointer;
  font-family: inherit;
  transition: background .15s;
  text-align: center;
}

.btn:hover {
  background: var(--primary-light);
  color: var(--text-inverse);
}

.btn:active {
  background: var(--primary-dark);
}

.btn:disabled {
  background: var(--bg-surface-alt);
  color: var(--text-muted);
  cursor: not-allowed;
}

.btn-green {
  background: rgba(16, 185, 129, 0.1);
  color: var(--secondary);
}

.btn-green:hover {
  background: var(--secondary);
  color: var(--text-inverse);
}

.btn-green:active {
  background: #0d9668;
}

.btn-cyan {
  background: rgba(6, 182, 212, 0.1);
  color: var(--miller-full);
}

.btn-cyan:hover {
  background: #06b6d4;
  color: var(--text-inverse);
}

.btn-cyan:active {
  background: var(--miller-full-dark);
}

.btn-orange {
  background: rgba(245, 158, 11, 0.1);
  color: var(--miller-output);
}

.btn-orange:hover {
  background: var(--cta);
  color: var(--text-inverse);
}

.btn-orange:active {
  background: #d97706;
}

.btn-row {
  display: flex;
  gap: 6px;
}

.btn-row .btn {
  flex: 1;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.form-row label {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-primary);
  min-width: 120px;
}

.form-row input[type="text"],
.form-row input[type="number"] {
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 3px 6px;
  color: var(--text-primary);
  font: 12px var(--font-sans);
  width: 110px;
  background: white;
}

.form-row select {
  font: 12px var(--font-sans);
  color: var(--text-primary);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 3px 6px;
  background: white;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.slider-row label {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-primary);
  width: 32px;
}

.slider-row input[type="range"] {
  flex: 1;
  accent-color: var(--primary);
}

.slider-row input[type="number"] {
  width: 72px;
  border: 1px solid var(--border);
  border-radius: 3px;
  padding: 2px 4px;
  color: var(--text-primary);
  font: 11px var(--font-sans);
  background: white;
}

.stat-labels {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.lbl-full {
  font: italic 11px var(--font-sans);
  color: var(--miller-full);
}

.lbl-output {
  font: italic 11px var(--font-sans);
  color: var(--miller-output);
}

.legend-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.legend-row span {
  font: 11px var(--font-sans);
}

.leg-cyan {
  color: var(--miller-full);
}

.leg-orange {
  color: var(--cta);
}

.check-row {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 400;
}

.check-row input[type="checkbox"] {
  accent-color: var(--primary);
  width: 14px;
  height: 14px;
}

.poni-status {
  font-weight: 400;
  font-size: 12px;
}

.poni-ok {
  color: var(--secondary);
}

.poni-no {
  color: var(--cta);
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.image-toolbar {
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 400;
  color: var(--text-primary);
  flex-shrink: 0;
}

.image-toolbar .zoom-info {
  color: var(--primary);
  min-width: 70px;
}

.image-toolbar .btn {
  padding: 4px 10px;
  font-size: 11px;
}

.image-toolbar .image-size-info {
  margin-left: auto;
  color: var(--text-secondary);
}

.image-area {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: var(--image-bg);
  cursor: grab;
}

.image-area:active {
  cursor: grabbing;
}

.image-area img {
  position: absolute;
  transform-origin: 0 0;
  image-rendering: pixelated;
  pointer-events: none;
  display: block;
  top: 0;
  left: 0;
}

.image-area .placeholder-text {
  color: var(--text-muted);
  font-size: 16px;
  text-align: center;
  line-height: 2;
  pointer-events: none;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(248,250,252,.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  font-size: 15px;
  font-weight: 400;
  color: var(--primary);
}

.spinner {
  width: 28px;
  height: 28px;
  border: 4px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin .7s linear infinite;
  margin-right: 10px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

[title] {
  cursor: help;
}

.visualizer.compact-mode {
  height: auto;
  min-height: 720px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.visualizer.compact-mode .main-content {
  min-height: 640px;
}

.visualizer.compact-mode .status-bar {
  padding: 2px 8px;
  font-size: 11px;
}

.visualizer.compact-mode .sidebar {
  width: 320px;
  min-width: 280px;
}

.visualizer.compact-mode .image-toolbar {
  padding: 3px 8px;
  font-size: 11px;
}

.visualizer.compact-mode .image-toolbar .btn {
  padding: 2px 8px;
  font-size: 10px;
}
</style>
