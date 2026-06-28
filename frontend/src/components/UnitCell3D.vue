<template>
  <div class="unit-cell-3d">
    <div v-if="isValid" class="visualization-section">
      <div class="view-controls">
        <button
          class="view-btn"
          :class="{ active: currentView === 'reset' }"
          @click="setView('reset')"
        >
          {{ t('results.viewReset') }}
        </button>
        <button
          class="view-btn"
          :class="{ active: currentView === 'a' }"
          @click="setView('a')"
        >
          {{ t('results.viewA') }}
        </button>
        <button
          class="view-btn"
          :class="{ active: currentView === 'b' }"
          @click="setView('b')"
        >
          {{ t('results.viewB') }}
        </button>
        <button
          class="view-btn"
          :class="{ active: currentView === 'c' }"
          @click="setView('c')"
        >
          {{ t('results.viewC') }}
        </button>
      </div>
      <!-- IMPORTANT: use v-if (never v-show). Plotly renders 0x0 inside display:none containers. -->
      <div ref="plotContainer" class="plot-container"></div>
    </div>
    <div v-else class="empty-state">
      {{ t('results.structure3DEmpty') }}
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps({
  /**
   * Cell parameters: { a, b, c, alpha, beta, gamma } — all Number.
   * Any field may be undefined / null / NaN; in that case the empty state is shown
   * and Plotly.newPlot is NOT called (avoids NaN geometry).
   */
  cellParams: {
    type: Object,
    default: null
  }
})

const { t } = useI18n()

const plotContainer = ref(null)
const currentView = ref('reset')

/**
 * Validate that every lattice parameter is a finite number.
 * Plotly.newPlot must never run against NaN geometry (produces broken traces).
 */
const isValidCellParams = (cp) => {
  if (!cp) return false
  const { a, b, c, alpha, beta, gamma } = cp
  return [a, b, c, alpha, beta, gamma].every(
    (v) => typeof v === 'number' && Number.isFinite(v)
  )
}

const isValid = computed(() => isValidCellParams(props.cellParams))

/**
 * Compute the three lattice vectors from cell parameters.
 * Geometry copied verbatim from ResultExport.vue:plot3DCell (lines 773-783).
 * Convention: va along X; vb in XY plane (angle gamma from va); vc resolved via
 * alpha/beta/gamma with the standard crystallographic formulas.
 */
const computeLatticeVectors = (cp) => {
  const { a, b, c, alpha, beta, gamma } = cp
  const alphaRad = (alpha * Math.PI) / 180
  const betaRad = (beta * Math.PI) / 180
  const gammaRad = (gamma * Math.PI) / 180

  const va = [a, 0, 0]
  const vb = [b * Math.cos(gammaRad), b * Math.sin(gammaRad), 0]
  const vc = [
    c * Math.cos(betaRad),
    (c * (Math.cos(alphaRad) - Math.cos(betaRad) * Math.cos(gammaRad))) / Math.sin(gammaRad),
    Math.sqrt(
      c * c -
        (c * Math.cos(betaRad)) ** 2 -
        (c * (Math.cos(alphaRad) - Math.cos(betaRad) * Math.cos(gammaRad)) /
          Math.sin(gammaRad)) **
          2
    )
  ]
  return { va, vb, vc }
}

/**
 * Build the 12 box edges + 3 axis vector traces and render via Plotly.newPlot.
 * Layout uses an orthographic camera so the wireframe reads as a true parallel
 * projection. Logic copied from ResultExport.vue:plot3DCell (lines 785-851).
 */
const renderPlot = () => {
  if (!plotContainer.value || !isValid.value) return
  if (typeof window === 'undefined') return

  const cp = props.cellParams
  const { va, vb, vc } = computeLatticeVectors(cp)

  // 8 corners of the parallelepiped.
  const p0 = [0, 0, 0]
  const p1 = va
  const p2 = vb
  const p3 = vc
  const p4 = va.map((v, i) => v + vb[i])
  const p5 = va.map((v, i) => v + vc[i])
  const p6 = vb.map((v, i) => v + vc[i])
  const p7 = va.map((v, i) => v + vb[i] + vc[i])

  // 12 edges of the unit cell wireframe.
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

  // 3 lattice axis vectors: a=red, b=green, c=blue.
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

  import('plotly.js-dist-min').then((Plotly) => {
    if (!plotContainer.value) return
    // Reset view selection whenever the plot is (re)drawn.
    currentView.value = 'reset'
    Plotly.newPlot(plotContainer.value, traces, layout, { displayModeBar: true })
    // Ensure the canvas matches the container size after dynamic import resolves.
    Plotly.Plots.resize(plotContainer.value)
  })
}

/**
 * Relayout the scene camera along one of the lattice axes (or reset to iso).
 * Camera math copied from ResultExport.vue:setView (lines 646-690):
 * each axis eye is the unit vector of the lattice direction scaled by 2.
 */
const setView = (view) => {
  currentView.value = view
  if (!plotContainer.value || typeof window === 'undefined') return
  if (!isValid.value) return

  import('plotly.js-dist-min').then((Plotly) => {
    if (!plotContainer.value) return
    const { va, vb, vc } = computeLatticeVectors(props.cellParams)

    const normA = Math.sqrt(va[0] ** 2 + va[1] ** 2 + va[2] ** 2)
    const normB = Math.sqrt(vb[0] ** 2 + vb[1] ** 2 + vb[2] ** 2)
    const normC = Math.sqrt(vc[0] ** 2 + vc[1] ** 2 + vc[2] ** 2)

    const camA = [va[0] / normA * 2, va[1] / normA * 2, va[2] / normA * 2]
    const camB = [vb[0] / normB * 2, vb[1] / normB * 2, vb[2] / normB * 2]
    const camC = [vc[0] / normC * 2, vc[1] / normC * 2, vc[2] / normC * 2]

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

const handleResize = () => {
  if (!plotContainer.value || typeof window === 'undefined') return
  import('plotly.js-dist-min').then((Plotly) => {
    if (plotContainer.value) Plotly.Plots.resize(plotContainer.value)
  })
}

// Re-render whenever cellParams change (deep watch for nested mutations).
watch(
  () => props.cellParams,
  (newVal) => {
    if (isValidCellParams(newVal)) {
      // v-if just rendered (or already had rendered) the container — wait for DOM.
      nextTick(() => renderPlot())
    } else if (plotContainer.value && typeof window !== 'undefined') {
      // Became invalid: purge any existing plot to free WebGL context + DOM nodes.
      import('plotly.js-dist-min').then((Plotly) => {
        if (plotContainer.value) Plotly.purge(plotContainer.value)
      })
    }
  },
  { deep: true }
)

onMounted(() => {
  if (isValid.value) {
    // Container exists (v-if=true) but ref is only safe after nextTick.
    nextTick(() => renderPlot())
  }
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (plotContainer.value && typeof window !== 'undefined') {
    // Best-effort cleanup; dynamic import may not resolve before teardown,
    // so guard with the resolved-module check inside the callback.
    import('plotly.js-dist-min').then((Plotly) => {
      if (plotContainer.value) Plotly.purge(plotContainer.value)
    }).catch(() => {})
  }
})
</script>

<style scoped>
.unit-cell-3d {
  width: 100%;
}

.view-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
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
  width: 100%;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  padding: 24px;
  background: var(--bg-surface);
  border: 1px dashed var(--border);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 0.875rem;
  text-align: center;
}
</style>
