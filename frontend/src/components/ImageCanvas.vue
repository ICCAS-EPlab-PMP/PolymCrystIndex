<template>
  <div class="canvas-wrap" :style="{ cursor: imageSrc ? (isPanning ? 'grabbing' : 'grab') : 'default' }" ref="wrapRef"
    @wheel.prevent="onWheel"
    @mousedown="onMouseDown"
    @mousemove="onMouseMove"
    @mouseup="onMouseUp"
    @mouseleave="onMouseUp"
  >
    <canvas ref="canvasRef" @click="onCanvasClick" />
    <div class="zoom-controls">
      <button class="zoom-btn" @click="zoomIn" title="Zoom In">+</button>
      <span class="zoom-label">{{ Math.round(scale * 100) }}%</span>
      <button class="zoom-btn" @click="zoomOut" title="Zoom Out">−</button>
      <button class="zoom-btn" @click="resetView" title="Reset View">⟲</button>
    </div>
    <div v-if="!imageSrc" style="padding:40px; text-align:center; color:#888; font-size:13px;">
      请先加载图像文件
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  imageSrc:      { type: String,  default: null  },
  origWidth:     { type: Number,  default: 1     },
  origHeight:    { type: Number,  default: 1     },
  dispWidth:     { type: Number,  default: 1     },
  dispHeight:    { type: Number,  default: 1     },
  markers:       { type: Array,   default: () => [] },
  centerX:       { type: Number,  default: null  },
  centerY:       { type: Number,  default: null  },
  crosshairColor:{ type: String,  default: '#ffff00' },
})
const emit = defineEmits(['click'])

const canvasRef = ref(null)
const wrapRef   = ref(null)
let _img = null

const scale    = ref(1)
const transX   = ref(0)
const transY   = ref(0)
const isPanning = ref(false)
const panStart  = ref({ x: 0, y: 0, tx: 0, ty: 0 })

const MIN_SCALE = 0.1
const MAX_SCALE = 20
const ZOOM_FACTOR = 0.1

function draw() {
  const canvas = canvasRef.value
  if (!canvas || !_img) return
  const wrap = wrapRef.value
  const dw = wrap.clientWidth  || _img.naturalWidth
  const dh = Math.round(dw * _img.naturalHeight / _img.naturalWidth)

  canvas.width  = _img.naturalWidth
  canvas.height = _img.naturalHeight

  canvas.style.width  = dw + 'px'
  canvas.style.height = dh + 'px'

  const scaleX = props.dispWidth / props.origWidth
  const scaleY = props.dispHeight / props.origHeight

  const ctx = canvas.getContext('2d')
  ctx.setTransform(scale.value, 0, 0, -scale.value, transX.value, transY.value + canvas.height * scale.value)
  ctx.drawImage(_img, 0, 0)

  if (props.centerX != null && props.centerY != null) {
    const cx = props.centerX * scaleX
    const cy = props.centerY * scaleY
    ctx.strokeStyle = props.crosshairColor
    ctx.lineWidth = 2 / scale.value
    ctx.beginPath()
    ctx.moveTo(cx - 12, cy); ctx.lineTo(cx + 12, cy)
    ctx.moveTo(cx, cy - 12); ctx.lineTo(cx, cy + 12)
    ctx.stroke()
  }

  for (const m of props.markers) {
    const mx = m.x * scaleX
    const my = m.y * scaleY
    ctx.strokeStyle = m.color || '#ff0000'
    ctx.lineWidth   = 2 / scale.value
    ctx.strokeRect(mx - 4, my - 4, 8, 8)
    if (m.label) {
      ctx.save()
      ctx.scale(1, -1)
      ctx.font = `bold ${18 / scale.value}px Arial`
      ctx.fillStyle = m.color || '#ff0000'
      ctx.fillText(m.label, mx + 8, -(my - 6))
      ctx.restore()
    }
  }
}

function loadImage(src) {
  if (!src) { _img = null; scale.value = 1; transX.value = 0; transY.value = 0; redraw(); return }
  const img = new Image()
  img.onload = () => { _img = img; scale.value = 1; transX.value = 0; transY.value = 0; draw() }
  img.src = 'data:image/png;base64,' + src
}

function redraw() {
  const canvas = canvasRef.value
  if (!canvas) return
  if (!_img) { canvas.width = 0; canvas.height = 0; return }
  draw()
}

function onCanvasClick(e) {
  if (!_img || isPanning.value) return
  const rect = canvasRef.value.getBoundingClientRect()
  const canvas = canvasRef.value
  const screenX = e.clientX - rect.left
  const screenY = e.clientY - rect.top
  const canvasX = screenX * canvas.width / rect.width
  const canvasY = screenY * canvas.height / rect.height
  const ix = Math.round((canvasX - transX.value) / scale.value * (props.origWidth / props.dispWidth))
  const iy = Math.round((canvas.height * scale.value + transY.value - canvasY) / scale.value * (props.origHeight / props.dispHeight))
  emit('click', { imageX: ix, imageY: iy })
}

function onWheel(e) {
  if (!_img) return
  const rect = canvasRef.value.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top

  const oldScale = scale.value
  const delta = e.deltaY < 0 ? ZOOM_FACTOR : -ZOOM_FACTOR
  const newScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, oldScale * (1 + delta)))

  const wxImg = (mouseX - transX.value) / oldScale
  const wyImg = (mouseY - transY.value) / oldScale
  const newTx = mouseX - wxImg * newScale
  const newTy = mouseY - wyImg * newScale

  scale.value = newScale
  transX.value = newTx
  transY.value = newTy
  draw()
}

function onMouseDown(e) {
  if (e.button !== 0) return
  isPanning.value = true
  panStart.value = { x: e.clientX, y: e.clientY, tx: transX.value, ty: transY.value }
}

function onMouseMove(e) {
  if (!isPanning.value) return
  transX.value = panStart.value.tx + (e.clientX - panStart.value.x)
  transY.value = panStart.value.ty + (e.clientY - panStart.value.y)
  draw()
}

function onMouseUp() {
  isPanning.value = false
}

function zoomIn() {
  if (!_img) return
  const rect = canvasRef.value.getBoundingClientRect()
  const cx = rect.width / 2
  const cy = rect.height / 2
  const oldScale = scale.value
  const newScale = Math.min(MAX_SCALE, oldScale * (1 + ZOOM_FACTOR))
  const wxImg = (cx - transX.value) / oldScale
  const wyImg = (cy - transY.value) / oldScale
  scale.value = newScale
  transX.value = cx - wxImg * newScale
  transY.value = cy - wyImg * newScale
  draw()
}

function zoomOut() {
  if (!_img) return
  const rect = canvasRef.value.getBoundingClientRect()
  const cx = rect.width / 2
  const cy = rect.height / 2
  const oldScale = scale.value
  const newScale = Math.max(MIN_SCALE, oldScale * (1 - ZOOM_FACTOR))
  const wxImg = (cx - transX.value) / oldScale
  const wyImg = (cy - transY.value) / oldScale
  scale.value = newScale
  transX.value = cx - wxImg * newScale
  transY.value = cy - wyImg * newScale
  draw()
}

function resetView() {
  scale.value = 1
  transX.value = 0
  transY.value = 0
  draw()
}

watch(() => props.imageSrc,  (v) => loadImage(v))
watch(() => [props.markers, props.centerX, props.centerY], () => draw(), { deep: true })

const resizeObs = typeof ResizeObserver !== 'undefined'
  ? new ResizeObserver(() => draw()) : null

onMounted(() => {
  if (props.imageSrc) loadImage(props.imageSrc)
  if (resizeObs && wrapRef.value) resizeObs.observe(wrapRef.value)
})
onUnmounted(() => resizeObs?.disconnect())

defineExpose({ zoomIn, zoomOut, resetView, scale })
</script>

<style scoped>
.canvas-wrap {
  position: relative;
  width: 100%;
  background: #111;
  border-radius: var(--radius-md);
  overflow: hidden;
}

.canvas-wrap canvas {
  display: block;
  width: 100%;
  height: auto;
}

.zoom-controls {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  background: rgba(0,0,0,0.55);
  border-radius: 6px;
  padding: 4px 6px;
}

.zoom-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: rgba(255,255,255,0.15);
  color: #fff;
  border-radius: 4px;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  transition: background 0.15s;
}

.zoom-btn:hover {
  background: rgba(255,255,255,0.3);
}

.zoom-label {
  color: #ccc;
  font-size: 11px;
  min-width: 36px;
  text-align: center;
}
</style>
