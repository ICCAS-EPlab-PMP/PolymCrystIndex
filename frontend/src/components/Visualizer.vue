<template>
  <div class="visualizer" :class="{ 'compact-mode': compact }">
    <div class="top-bar">
      <span class="title">{{ t('visualizer.dataSource') }}：</span>
      <div class="source-group">
        <label>
          <input type="radio" v-model="activePanel" value="raw" />
          <span>{{ t('visualizer.rawImage') }} (.tif / .edf / .cbf / .h5)</span>
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
                ① {{ t('visualizer.importDiffractionImage') }}&nbsp;(.tif / .edf / .cbf / .h5)
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
                <button class="btn btn-gold" :disabled="!raw.imageLoaded"
                        @click="triggerUpload('rawReferencePoints')">
                  ★ {{ t('visualizer.importReferencePoints') }}
                </button>
              </div>
              <div class="stat-labels">
                <span class="lbl-full">{{ t('visualizer.fullMiller') }}: {{ raw.fullCount > 0 ? raw.fullCount + ' ' + t('visualizer.points') : t('visualizer.notLoaded') }}</span>
                <span class="lbl-output">{{ t('visualizer.outputMiller') }}: {{ raw.outputCount > 0 ? raw.outputCount + ' ' + t('visualizer.points') : t('visualizer.notLoaded') }}</span>
                <span class="lbl-ref">{{ t('visualizer.referencePointsCount', {count: raw.refCount}) }}</span>
              </div>
              <div class="btn-row">
                <button class="btn" :disabled="!raw.imageLoaded" @click="saveRawImage">{{ t('visualizer.saveMarkedImage') }}</button>
                <button class="btn" :disabled="!raw.imageLoaded || raw.fullCount === 0" @click="clearRawMillerType('full')">{{ t('visualizer.clearFullMiller') }}</button>
                <button class="btn" :disabled="!raw.imageLoaded || raw.outputCount === 0" @click="clearRawMillerType('output')">{{ t('visualizer.clearOutputMiller') }}</button>
                <button class="btn" :disabled="!raw.imageLoaded || raw.refCount === 0" @click="clearRawRef">{{ t('visualizer.clearReferencePoints') }}</button>
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
                <span class="leg-gold">★&nbsp;{{ t('visualizer.refPointLegend') }}</span>
              </div>
            </div>
          </div>

          <div class="group-box">
            <span class="group-title">{{ t('visualizer.boxIntegrateMode') }}</span>
            <div class="inner">
              <label class="check-row">
                <input type="checkbox" v-model="raw.boxMode" @change="onBoxModeChange" />
                {{ t('visualizer.boxIntegrateMode') }}
              </label>
              <div v-if="raw.boxMode" class="box-hint">{{ t('visualizer.boxIntegrateHint') }}</div>
              <div v-if="raw.boxMode" class="box-hint box-hint-pan">{{ t('visualizer.boxPanHint') }}</div>
              <div v-if="raw.box" class="btn-row">
                <button class="btn" :disabled="raw.boxLoading" @click="runBoxIntegrate">
                  ⟳ {{ t('visualizer.recomputeBox') }}
                </button>
                <button class="btn" @click="clearBox">{{ t('visualizer.clearBox') }}</button>
              </div>
              <div v-if="raw.box" class="box-info">
                {{ t('visualizer.boxInfo', { w: Math.abs(raw.box.x1-raw.box.x0)+1, h: Math.abs(raw.box.y1-raw.box.y0)+1 }) }}
                &nbsp;|&nbsp; {{ raw.boxResult ? (raw.boxResult.miller_in_box_count + ' ' + t('visualizer.millerInBox')) : '' }}
              </div>
              <!-- 阈值:积分时只统计 [min,max] 强度区间的像素,去除坏信号 -->
              <div v-if="raw.boxMode" class="box-thresh">
                <span class="box-thresh-title">{{ t('visualizer.boxThreshold') }}</span>
                <div class="form-row">
                  <label>{{ t('visualizer.boxThreshMin') }}:</label>
                  <input type="number" v-model.number="raw.boxThreshMin" step="any" />
                </div>
                <div class="form-row">
                  <label>{{ t('visualizer.boxThreshMax') }}:</label>
                  <input type="number" v-model.number="raw.boxThreshMax" step="any" />
                </div>
                <div class="btn-row">
                  <button class="btn" :disabled="!raw.box || raw.boxLoading" @click="runBoxIntegrate">
                    {{ t('visualizer.applyThreshold') }}
                  </button>
                  <button class="btn" @click="resetBoxThreshold">{{ t('visualizer.resetThreshold') }}</button>
                </div>
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
             <img v-if="raw.imageSrc" ref="rawImageEl" :src="'data:image/png;base64,' + raw.imageSrc"
                  :style="rawImgStyle" draggable="false" @load="handleImageLoad('raw')" />
            <canvas v-if="raw.imageSrc && raw.boxMode" ref="rawOverlayEl" class="overlay-canvas"
                    :style="rawOverlayStyle"
                    @mousedown.stop.prevent="onBoxDown"
                    @mousemove.stop="onBoxMove"
                    @mouseup.stop="onBoxUp"
                    @mouseleave="onBoxUp"
                    @wheel.prevent="onWheel($event,'raw')"></canvas>
            <div class="placeholder-text" v-else>
              {{ t('visualizer.pleaseImportDiffractionImage') }}<br/>
              (.tif / .edf / .cbf / .h5)
              <template v-if="raw.fullCount > 0 || raw.outputCount > 0 || raw.refCount > 0">
                <br/>
                FullMiller: {{ raw.fullCount }} / outputMiller: {{ raw.outputCount }} / Ref: {{ raw.refCount }}
              </template>
            </div>
          </div>

          <div v-if="raw.boxResult" class="box-result-panel">
            <div class="box-result-header">
              <span class="box-result-title">{{ t('visualizer.boxProfile') }}</span>
              <div class="box-xaxis-switch">
                <span class="box-unit-label">{{ t('visualizer.displayUnit') }}:</span>
                <label><input type="radio" v-model="raw.boxUnit" value="px" @change="onUnitChange" />{{ t('visualizer.xAxisPx') }}</label>
                <label><input type="radio" v-model="raw.boxUnit" value="q" @change="onUnitChange" />{{ t('visualizer.xAxisQ') }}</label>
                <label><input type="radio" v-model="raw.boxUnit" value="2th" @change="onUnitChange" />{{ t('visualizer.xAxis2theta') }}</label>
                <label><input type="radio" v-model="raw.boxUnit" value="d" @change="onUnitChange" />{{ t('visualizer.xAxisD') }}</label>
              </div>
              <button class="btn btn-small" @click="exportBoxProfileCsv">{{ t('visualizer.exportProfileCsv') }}</button>
            </div>
            <div v-if="boxCoverageText" class="box-coverage">{{ t('visualizer.boxCoverage') }}: {{ boxCoverageText }}</div>
            <div ref="boxChartEl" class="box-chart"></div>

            <div class="box-result-header" style="margin-top:8px;">
              <span class="box-result-title">{{ t('visualizer.boxMillerList') }} ({{ raw.boxResult.miller_in_box_count }})</span>
              <button class="btn btn-small" @click="exportBoxMillerTxt">{{ t('visualizer.exportMillerTxt') }}</button>
            </div>
            <div class="box-miller-table-wrap">
              <table v-if="raw.boxResult.miller_in_box.length" class="box-miller-table">
                <thead>
                  <tr>
                    <th>h</th><th>k</th><th>l</th>
                    <th>q (Å⁻¹)</th><th>ψ (°)</th><th>2θ (°)</th><th>d (Å)</th>
                    <th>x (px)</th><th>y (px)</th><th>intensity</th>
                    <th>{{ t('visualizer.source') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(m, i) in sortedMillerInBox" :key="i">
                    <td>{{ m.h }}</td><td>{{ m.k }}</td><td>{{ m.l }}</td>
                    <td>{{ fmt(m.q) }}</td><td>{{ fmt(m.psi) }}</td>
                    <td>{{ fmt(m.two_theta) }}</td><td>{{ fmt(m.d_spacing) }}</td>
                    <td>{{ m.x }}</td><td>{{ m.y }}</td>
                    <td>{{ m.intensity != null ? m.intensity.toFixed(1) : '—' }}</td>
                    <td>{{ m.overlay_label || (m.overlay_index === 0 ? t('visualizer.fullMiller') : t('visualizer.outputMiller')) }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="placeholder-text" style="padding:16px;">{{ t('visualizer.noMillerInBox') }}</div>
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
                <button class="btn btn-gold" :disabled="!int2d.imageLoaded"
                        @click="triggerUpload('intReferencePoints')">
                  ★ {{ t('visualizer.importReferencePoints') }}
                </button>
              </div>
              <div class="stat-labels">
                <span class="lbl-full">{{ t('visualizer.fullMiller') }}: {{ int2d.fullCount > 0 ? int2d.fullCount + ' ' + t('visualizer.points') : t('visualizer.notLoaded') }}</span>
                <span class="lbl-output">{{ t('visualizer.outputMiller') }}: {{ int2d.outputCount > 0 ? int2d.outputCount + ' ' + t('visualizer.points') : t('visualizer.notLoaded') }}</span>
                <span class="lbl-ref">{{ t('visualizer.referencePointsCount', {count: int2d.refCount}) }}</span>
              </div>
              <div class="btn-row">
                <button class="btn" :disabled="!int2d.imageLoaded" @click="saveIntImage">{{ t('visualizer.saveMarkedImage') }}</button>
                <button class="btn" :disabled="!int2d.imageLoaded || int2d.fullCount === 0" @click="clearIntMillerType('full')">{{ t('visualizer.clearFullMiller') }}</button>
                <button class="btn" :disabled="!int2d.imageLoaded || int2d.outputCount === 0" @click="clearIntMillerType('output')">{{ t('visualizer.clearOutputMiller') }}</button>
                <button class="btn" :disabled="!int2d.imageLoaded || int2d.refCount === 0" @click="clearIntRef">{{ t('visualizer.clearReferencePoints') }}</button>
                <button class="btn" :disabled="!int2d.imageLoaded" @click="clearIntMiller">{{ t('visualizer.clearAllMarkers') }}</button>
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
                <span class="leg-gold">★&nbsp;{{ t('visualizer.refPointLegend') }}</span>
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
             <img v-if="int2d.imageSrc" ref="intImageEl" :src="'data:image/png;base64,' + int2d.imageSrc"
                  :style="intImgStyle" draggable="false" @load="handleImageLoad('int')" />
            <div class="placeholder-text" v-else>
              {{ t('visualizer.pleaseImport2DIntegrationImage') }}<br/>
              (.npy / .tif)
            </div>
          </div>
        </div>
      </template>
    </div>

    <div v-if="hdf5Picker.open" class="hdf5-picker-overlay">
      <div class="hdf5-picker-card">
        <div class="hdf5-picker-title">
          {{ t('visualizer.hdf5SelectTitle') }}
          <span class="hdf5-picker-filename">{{ hdf5Picker.filename }}</span>
        </div>

        <div class="hdf5-picker-row">
          <label class="hdf5-label">Dataset</label>
          <select v-model="hdf5Picker.selectedPath" class="hdf5-select">
            <option v-for="ds in hdf5Picker.datasets" :key="ds.path" :value="ds.path">
              {{ ds.path }} &nbsp;[shape {{ ds.shape.join('×') }}, {{ ds.ndim }}D, {{ ds.dtype }}]
            </option>
          </select>
        </div>

        <div v-if="hdf5ExtraAxes.length === 0" class="hdf5-info">
          {{ t('visualizer.hdf5NoExtraAxes') }}
        </div>

        <div v-for="ax in hdf5ExtraAxes" :key="ax.axis" class="hdf5-axis-row">
          <span class="hdf5-axis-label">{{ t('visualizer.hdf5Axis') }} #{{ ax.axis }} ({{ ax.size }})</span>
          <select v-model="ax.choice.mode" class="hdf5-select hdf5-axis-mode">
            <option value="index">{{ t('visualizer.hdf5ModeIndex') }}</option>
            <option value="max">{{ t('visualizer.hdf5ModeMax') }}</option>
            <option value="sum">{{ t('visualizer.hdf5ModeSum') }}</option>
            <option value="mean">{{ t('visualizer.hdf5ModeMean') }}</option>
          </select>
          <input v-if="ax.choice.mode === 'index'" type="number"
                 v-model.number="ax.choice.index" :min="0" :max="ax.size - 1"
                 class="hdf5-axis-index" />
          <span v-else class="hdf5-projection-hint">{{ t('visualizer.hdf5ProjectionHint') }}</span>
        </div>

        <div class="hdf5-picker-actions">
          <button class="btn btn-green" @click="loadHdf5Slice">{{ t('visualizer.hdf5Load') }}</button>
          <button class="btn" @click="cancelHdf5Picker">{{ t('common.cancel') }}</button>
        </div>
      </div>
    </div>

    <div class="status-bar">{{ statusMsg }}</div>

    <input ref="fileRawImage"    type="file" accept=".tif,.tiff,.edf,.cbf,.img,.h5,.hdf5" style="display:none" @change="e=>onFileChange(e,'rawImage')" />
    <input ref="fileRawPoni"     type="file" accept=".poni" style="display:none" @change="e=>onFileChange(e,'rawPoni')" />
    <input ref="fileRawFull"     type="file" accept=".txt" style="display:none" @change="e=>onFileChange(e,'rawFullMiller')" />
    <input ref="fileRawOutput"   type="file" accept=".txt" style="display:none" @change="e=>onFileChange(e,'rawOutputMiller')" />
    <input ref="fileIntImage"    type="file" accept=".npy,.tif,.tiff" style="display:none" @change="e=>onFileChange(e,'intImage')" />
    <input ref="fileIntInfo"     type="file" accept=".txt" style="display:none" @change="e=>onFileChange(e,'intInfo')" />
    <input ref="fileIntFull"     type="file" accept=".txt" style="display:none" @change="e=>onFileChange(e,'intFullMiller')" />
    <input ref="fileIntOutput"   type="file" accept=".txt" style="display:none" @change="e=>onFileChange(e,'intOutputMiller')" />
    <input ref="fileRawRef"      type="file" accept=".txt,.csv" style="display:none" @change="e=>onFileChange(e,'rawReferencePoints')" />
    <input ref="fileIntRef"      type="file" accept=".txt,.csv" style="display:none" @change="e=>onFileChange(e,'intReferencePoints')" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
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

const raw = reactive({
  imageLoaded: false,
  imageSrc: '',
  imgW: 0, imgH: 0,
  imgMin: 0, imgMax: 65535,
  poniLoaded: false,
  fullCount: 0,
  outputCount: 0,
  refCount: 0,
  zoom: 1.0,
  panX: 0, panY: 0,
  p: {
    wl: 1.0, px: 100, py: 100, cx: 0, cy: 0, dist: 1000, rot: 0.0,
    quadrant: '第一象限', mode: 'Linear', colormap: '灰度',
    cmin: 0, cmax: 65535, showLabels: true,
  },
  // —— 方框积分模式 ——
  boxMode: false,         // 是否处于"画方框"模式
  box: null,              // 已确认的矩形 {x0,y0,x1,y1}（图像像素）
  boxDrawing: null,       // 拖拽中的临时矩形
  boxResult: null,        // 后端返回的积分结果
  boxUnit: 'q',           // 显示/报告单位：'px' | 'q' | '2th' | 'd'（联动曲线轴、覆盖范围、hkl表排序）
  boxLoading: false,
  // 方框积分的阈值(默认全范围;低于/高于此强度的像素在积分与 hkl intensity 中视为坏信号)
  boxThreshMin: 0,
  boxThreshMax: 65535,
})

const int2d = reactive({
  imageLoaded: false,
  imageSrc: '',
  imgMin: 0, imgMax: 65535,
  fullCount: 0,
  outputCount: 0,
  refCount: 0,
  zoom: 1.0,
  panX: 0, panY: 0,
  p: {
    qMin: 0.0, qMax: 1.0, azMin: -180.0, azMax: 180.0,
    colormap: '灰度', mode: 'Linear', cmin: 0, cmax: 65535,
    convention: 'ccw', psiOffset: 0.0,
    azCropEnabled: false, azCropMin: -30.0, azCropMax: 120.0,
  },
})

const rawCanvas = ref(null)
const intCanvas = ref(null)
const rawImageEl = ref(null)
const intImageEl = ref(null)
const rawOverlayEl = ref(null)   // 方框积分的 canvas 叠加层
const boxChartEl = ref(null)     // 方框积分曲线的 Plotly 容器
const fileRawImage = ref(null)

// —— HDF5 dataset/切片选择面板 ——
const hdf5Picker = reactive({
  open: false,           // 是否显示选择面板
  fileKey: '',           // probe 返回的 file_key
  filename: '',
  datasets: [],          // [{path, shape, ndim, dtype, size}]
  selectedPath: '',      // 当前选中的 dataset path
  // 每个"额外维"的选择：axis(原 dataset 轴号) → {mode, index}
  // 额外维 = 除最后两维外的所有维
  axisChoices: {},       // {axisIndex: {mode:'index'|'max'|'sum'|'mean', index:number}}
})
const fileRawPoni = ref(null)
const fileRawFull = ref(null)
const fileRawOutput = ref(null)
const fileRawRef = ref(null)
const fileIntImage = ref(null)
const fileIntInfo = ref(null)
const fileIntFull = ref(null)
const fileIntOutput = ref(null)
const fileIntRef = ref(null)

const rawImgStyle = computed(() => ({
  transform: `translate(${raw.panX}px, ${raw.panY}px) scale(${raw.zoom})`,
  transformOrigin: '0 0',
}))

// 叠加层 canvas 的样式:只用 transform(与 <img> 同源)。canvas 的 CSS 尺寸
// 由 .overlay-canvas 的 `max-width:100%; height:auto` + canvas 的
// width/height 属性(= imgW/imgH)共同决定 —— 这与 <img> 受全局
// `img{max-width:100%;height:auto}` 的尺寸计算路径完全一致,故二者 layout
// 尺寸严格相等,经同一 transform 后像素级重合。
// 关键:不要在这里显式设 width/height,否则会覆盖 max-width/height:auto 的
// 等比缩放,导致与 <img> 不一致(即"方框不跟手"的根因)。
const rawOverlayStyle = computed(() => ({
  transform: `translate(${raw.panX}px, ${raw.panY}px) scale(${raw.zoom})`,
  transformOrigin: '0 0',
}))

const intImgStyle = computed(() => ({
  transform: `translate(${int2d.panX}px, ${int2d.panY}px) scale(${int2d.zoom})`,
  transformOrigin: '0 0',
}))

const indexedOverlayGroups = ref([])

const effectiveOverlayGroups = computed(() => {
  if (props.overlayGroups?.length) return props.overlayGroups
  if (props.resultType === 'indexing') return indexedOverlayGroups.value
  return []
})

function setStatus(msg) { statusMsg.value = msg }

function clampZoom(panel) {
  const s = panel === 'raw' ? raw : int2d
  s.zoom = Math.max(0.02, Math.min(s.zoom, 50))
}

const resetZoomTimers = { raw: null, int: null }
const preserveViewOnNextImageLoad = reactive({ raw: false, int: false })

function scheduleResetZoom(panel, retries = 6) {
  if (resetZoomTimers[panel]) {
    clearTimeout(resetZoomTimers[panel])
  }
  resetZoomTimers[panel] = setTimeout(() => {
    resetZoomTimers[panel] = null
    resetZoom(panel, retries)
  }, 16)
}

function getPanelImageMetrics(panel, container) {
  const imageEl = panel === 'raw' ? rawImageEl.value : intImageEl.value
  const naturalWidth = imageEl?.naturalWidth || 0
  const naturalHeight = imageEl?.naturalHeight || 0
  if (naturalWidth > 0 && naturalHeight > 0) {
    return { width: naturalWidth, height: naturalHeight }
  }
  if (panel === 'raw' && raw.imgW > 0 && raw.imgH > 0) {
    return { width: raw.imgW, height: raw.imgH }
  }
  return {
    width: container.clientWidth || 0,
    height: container.clientHeight || 0,
  }
}

function resetZoom(panel, retries = 0) {
  const s = panel === 'raw' ? raw : int2d
  const container = panel === 'raw' ? rawCanvas.value : intCanvas.value
  if (!container) return
  const cw = container.clientWidth, ch = container.clientHeight
  const { width: iw, height: ih } = getPanelImageMetrics(panel, container)
  if (cw <= 0 || ch <= 0 || iw <= 0 || ih <= 0) {
    if (retries > 0) {
      scheduleResetZoom(panel, retries - 1)
    }
    return
  }
  const scaleX = cw / iw, scaleY = ch / ih
  s.zoom = Math.min(scaleX, scaleY)
  s.panX = (cw - iw * s.zoom) / 2
  s.panY = (ch - ih * s.zoom) / 2
}

function handleImageLoad(panel) {
  if (preserveViewOnNextImageLoad[panel]) {
    preserveViewOnNextImageLoad[panel] = false
    return
  }
  scheduleResetZoom(panel, 8)
}

function setPreserveView(panel, preserve = true) {
  preserveViewOnNextImageLoad[panel] = preserve
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

// ============ 方框积分（Box Integration） ============

// 屏幕(clientX/Y)坐标 → "全分辨率探测器像素"坐标(后端 image[y,x] 数组的索引)。
//
// 关键:不信任 panX/panY/zoom 的解析值,而是直接测量 <img> 在屏幕上"变换后"
// 的真实渲染矩形(getBoundingClientRect 返回的是 transform 生效后的盒子),
// 把鼠标位置按比例映射到"全分辨率像素"。这样即使:
//   - PNG 被浏览器/内存以不同尺寸渲染(naturalWidth ≠ imgW),
//   - resetZoom 的 zoom 计算与实际显示脱节,
//   - 布局抖动,
// 映射仍然落到正确的后端像素。
//
// 注意:全分辨率像素 == 后端 image_shape(后端 PNG 由 to_pil_image 按原始
// shape 渲染,无缩放,故 naturalWidth 通常 == imgW;但即便不等,这里用 imgW
// 作为分子,保证发给后端的坐标永远是后端数组的真实索引)。
function screenToImagePx(e) {
  const img = rawImageEl.value
  if (!img) return { x: 0, y: 0 }
  const rect = img.getBoundingClientRect()
  if (rect.width <= 0 || rect.height <= 0) return { x: 0, y: 0 }
  const fullW = raw.imgW || img.naturalWidth || 1   // 全分辨率(后端数组宽度)
  const fullH = raw.imgH || img.naturalHeight || 1
  // 鼠标相对于 <img> 渲染盒左上角的比例 → 全分辨率像素
  const fx = (e.clientX - rect.left) / rect.width
  const fy = (e.clientY - rect.top) / rect.height
  const ix = Math.round(fx * fullW)
  const iy = Math.round(fy * fullH)
  return {
    x: Math.max(0, Math.min(fullW - 1, ix)),
    y: Math.max(0, Math.min(fullH - 1, iy)),
  }
}

function onBoxModeChange() {
  // 进入/退出画框模式时清理临时态；canvas 由 v-if=raw.boxMode 控制
  raw.boxDrawing = null
  if (!raw.boxMode) {
    // 退出模式：保留已确认 box 与结果，仅停止接收新绘制
  }
  nextTick(() => drawOverlay())
}

// 框选模式下:Shift+拖动 = 平移(复用 startDrag/onDrag);普通拖动 = 画框;
// 滚轮 = 缩放(canvas 的 @wheel 已转发到 onWheel)。
// boxDrag.kind: null | 'pan' | 'box'
const boxDrag = reactive({ kind: null, lastX: 0, lastY: 0 })

function onBoxDown(e) {
  if (!raw.boxMode || e.button !== 0) return
  if (e.shiftKey) {
    // Shift+拖动 → 平移,复用既有 startDrag/onDrag 的 drag 状态
    boxDrag.kind = 'pan'
    boxDrag.lastX = e.clientX
    boxDrag.lastY = e.clientY
    drag.active = true
    drag.panel = 'raw'
    drag.lastX = e.clientX
    drag.lastY = e.clientY
  } else {
    // 普通拖动 → 画框
    boxDrag.kind = 'box'
    const { x, y } = screenToImagePx(e)
    raw.boxDrawing = { x0: x, y0: y, x1: x, y1: y }
  }
}

function onBoxMove(e) {
  if (!raw.boxMode || !boxDrag.kind) return
  if (boxDrag.kind === 'pan') {
    // 平移:直接复用 onDrag 逻辑(修改 raw.panX/panY)
    onDrag(e, 'raw')
    return
  }
  // 画框
  const { x, y } = screenToImagePx(e)
  raw.boxDrawing.x1 = x
  raw.boxDrawing.y1 = y
  drawOverlay()
}

function onBoxUp() {
  if (!raw.boxMode) return
  const kind = boxDrag.kind
  boxDrag.kind = null
  if (kind === 'pan') {
    drag.active = false
    return
  }
  if (kind !== 'box' || !raw.boxDrawing) return
  const d = raw.boxDrawing
  raw.boxDrawing = null
  const x0 = Math.min(d.x0, d.x1), x1 = Math.max(d.x0, d.x1)
  const y0 = Math.min(d.y0, d.y1), y1 = Math.max(d.y0, d.y1)
  // 面积过小视为误点击，丢弃
  if (x1 - x0 < 3 || y1 - y0 < 3) {
    drawOverlay()
    return
  }
  // 裁剪到图像范围 —— 用全分辨率像素(权威来源),与 screenToImagePx 一致
  const fullW = raw.imgW - 1, fullH = raw.imgH - 1
  const cx0 = Math.max(0, Math.min(x0, fullW)), cy0 = Math.max(0, Math.min(y0, fullH))
  const cx1 = Math.max(0, Math.min(x1, fullW)), cy1 = Math.max(0, Math.min(y1, fullH))
  if (cx1 <= cx0 || cy1 <= cy0) { drawOverlay(); return }
  raw.box = { x0: cx0, y0: cy0, x1: cx1, y1: cy1 }
  drawOverlay()
  runBoxIntegrate()
}

function clearBox() {
  raw.box = null
  raw.boxResult = null
  raw.boxDrawing = null
  drawOverlay()
}

// 阈值复位到全范围 [0, 图像最大值](即不做强度过滤)
function resetBoxThreshold() {
  raw.boxThreshMin = 0
  raw.boxThreshMax = raw.imgMax || 65535
  if (raw.box) runBoxIntegrate()
}

// 把叠加层 canvas 的内部尺寸对齐到"全分辨率像素"(raw.imgW/imgH,与后端
// image 数组同尺寸),并画方框。canvas 与 <img> 共用 rawImgStyle(transform),
// canvas 的 CSS 默认尺寸 = 其 width 属性(= 全分辨率像素)。
//
// 关键一致性:raw.box / raw.boxDrawing 的坐标都是"全分辨率像素"(screenToImagePx
// 产出),canvas buffer 也是全分辨率像素,故方框画出来与发给后端的坐标严格对应。
// 即使 PNG 的 naturalWidth 与 imgW 不严格相等(罕见),只要 canvas 与 <img>
// 共用同一 transform,且 canvas buffer == imgW、<img> CSS 尺寸 == naturalWidth,
// 二者仍会同比例缩放显示 —— 方框的视觉位置即代表真实积分区域。
function drawOverlay() {
  const canvas = rawOverlayEl.value
  if (!canvas) return
  const w = raw.imgW, h = raw.imgH
  if (!w || !h) return
  // 仅在尺寸变化时重设 buffer(避免每帧重设引起闪烁/清空)
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w
    canvas.height = h
  }
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, w, h)

  const drawRect = (r, color, lineW, dashed) => {
    if (!r) return
    ctx.strokeStyle = color
    ctx.lineWidth = lineW
    ctx.setLineDash(dashed ? [8, 6] : [])
    const x = Math.min(r.x0, r.x1), y = Math.min(r.y0, r.y1)
    const rw = Math.abs(r.x1 - r.x0), rh = Math.abs(r.y1 - r.y0)
    ctx.strokeRect(x, y, rw, rh)
    ctx.setLineDash([])
    // 四角小标记,缩放后仍可见
    const c = Math.max(3, lineW + 1)
    ctx.fillStyle = color
    ctx.fillRect(x - c, y - c, c * 2, c * 2)
    ctx.fillRect(x + rw - c, y - c, c * 2, c * 2)
    ctx.fillRect(x - c, y + rh - c, c * 2, c * 2)
    ctx.fillRect(x + rw - c, y + rh - c, c * 2, c * 2)
  }
  if (raw.box) drawRect(raw.box, 'rgba(255,215,0,0.95)', 3, false)
  if (raw.boxDrawing) drawRect(raw.boxDrawing, 'rgba(0,200,255,0.9)', 2.5, true)
}

async function runBoxIntegrate() {
  if (!raw.box) return
  raw.boxLoading = true
  loading.value = true
  try {
    const { data } = await axios.post(`${API_BASE}/raw/integrate-box`, {
      x0: raw.box.x0, y0: raw.box.y0, x1: raw.box.x1, y1: raw.box.y1,
      npt: 500,
      threshold_min: Number(raw.boxThreshMin),
      threshold_max: Number(raw.boxThreshMax),
      wl: parseFloat(raw.p.wl) || 1,
      px: parseFloat(raw.p.px) || 100,
      py: parseFloat(raw.p.py) || 100,
      cx: parseFloat(raw.p.cx) || 0,
      cy: parseFloat(raw.p.cy) || 0,
      dist: parseFloat(raw.p.dist) || 1000,
      quadrant: raw.p.quadrant,
      rot_offset: parseFloat(raw.p.rot) || 0,
      use_pyfai: true,
    })
    raw.boxResult = data
    setStatus(`${t('visualizer.boxProfile')}: ${data.miller_in_box_count} ${t('visualizer.millerInBox')}`)
    await nextTick()
    await drawBoxChart()
  } catch (err) {
    const msg = err.response?.data?.detail || err.message
    setStatus('Box integrate error: ' + msg)
    window.$toast?.(t('visualizer.boxIntegrateFailed') + ': ' + msg, true)
  } finally {
    raw.boxLoading = false
    loading.value = false
  }
}

// 单位切换：重绘曲线（hkl 表由 sortedMillerInBox 自动响应）
function onUnitChange() {
  nextTick(() => drawBoxChart())
}

// 在单调(近似)的曲线 x 上,对给定 xv 线性插值出 y。None/NaN 视为断点。
// 返回插值 y,或 null(超出范围或两侧都缺失)。
function _interpCurveY(curveX, curveY, xv) {
  const n = curveX.length
  if (!n) return null
  // 找到第一个 >= xv 的索引
  let hi = 0
  while (hi < n && (curveX[hi] == null || curveX[hi] < xv)) hi++
  if (hi === 0) {
    // xv 在最左:用第一个有效 y
    return _firstValidY(curveY, 0)
  }
  if (hi >= n) {
    // xv 在最右:用最后一个有效 y
    return _lastValidY(curveY, n - 1)
  }
  // 在 hi-1 与 hi 之间插值;跳过 NaN
  let lo = hi - 1
  while (lo > 0 && (curveY[lo] == null || (typeof curveY[lo] === 'number' && isNaN(curveY[lo])))) lo--
  let hi2 = hi
  while (hi2 < n - 1 && (curveY[hi2] == null || (typeof curveY[hi2] === 'number' && isNaN(curveY[hi2])))) hi2++
  const x0 = curveX[lo], x1 = curveX[hi2], y0 = curveY[lo], y1 = curveY[hi2]
  if (x0 == null || x1 == null || y0 == null || y1 == null) return null
  if (x1 === x0) return y0
  const t = (xv - x0) / (x1 - x0)
  return y0 + t * (y1 - y0)
}
function _firstValidY(arr, from) {
  for (let i = from; i < arr.length; i++) {
    const v = arr[i]
    if (v != null && !(typeof v === 'number' && isNaN(v))) return v
  }
  return null
}
function _lastValidY(arr, from) {
  for (let i = from; i >= 0; i--) {
    const v = arr[i]
    if (v != null && !(typeof v === 'number' && isNaN(v))) return v
  }
  return null
}

async function drawBoxChart() {
  const r = raw.boxResult
  const el = boxChartEl.value
  if (!r || !el) return
  const Plotly = (await import('plotly.js-dist-min')).default
  let x, xtitle
  if (raw.boxUnit === '2th') { x = r.two_theta; xtitle = '2θ (°)' }
  else if (raw.boxUnit === 'd') { x = r.d_spacing; xtitle = 'd (Å)' }
  else if (raw.boxUnit === 'px') {
    // 像素单位：用 bin 序号作为 x（无物理意义，仅作示意）
    x = r.q_values.map((_, i) => i)
    xtitle = t('visualizer.xAxisPx')
  }
  else { x = r.q_values; xtitle = 'q (Å⁻¹)' }
  const trace = {
    x, y: r.i_q,
    mode: 'lines+markers', line: { color: '#2499f8', width: 2 },
    marker: { size: 4, color: '#2499f8' },
    connectgaps: false,
  }

  // —— 在曲线上用黄色星标识方框内每个 Miller 点(当前单位的 x 位置) ——
  // 对每个点,在曲线 x 轴上线性插值得到其强度 y,落在曲线上。
  const traces = [trace]
  if (r.miller_in_box && r.miller_in_box.length && raw.boxUnit !== 'px') {
    const key = raw.boxUnit === '2th' ? 'two_theta'
      : raw.boxUnit === 'd' ? 'd_spacing' : 'q'
    const curveX = x  // 与 trace.x 同源(已按单位选取)
    const curveY = r.i_q
    const starX = [], starY = [], starText = []
    for (const m of r.miller_in_box) {
      const mx = m[key]
      if (mx == null) continue
      // 在曲线 x(单调递增)上插值找 y
      const my = _interpCurveY(curveX, curveY, mx)
      if (my == null || !isFinite(my)) continue
      starX.push(mx)
      starY.push(my)
      starText.push(`${m.h} ${m.k} ${m.l}`)
    }
    if (starX.length) {
      traces.push({
        x: starX, y: starY, text: starText,
        mode: 'markers',
        marker: {
          symbol: 'star', size: 14, color: '#ffd700',
          line: { color: '#b8860b', width: 1 },
        },
        hoverinfo: 'text+x+y',
        hoverlabel: { bgcolor: '#fff8dc' },
        showlegend: false,
      })
    }
  }

  const layout = {
    margin: { l: 55, r: 16, t: 10, b: 40 },
    xaxis: { title: xtitle, gridcolor: '#e5e7eb' },
    yaxis: { title: t('visualizer.intensity'), gridcolor: '#e5e7eb' },
    paper_bgcolor: '#fff', plot_bgcolor: '#fff',
    font: { size: 12 },
    showlegend: false,
    height: 280,
  }
  const config = { displayModeBar: false, responsive: true }
  Plotly.react(el, traces, layout, config)
}

function fmt(v) {
  if (v == null || (typeof v === 'number' && isNaN(v))) return '—'
  return (typeof v === 'number') ? v.toFixed(4) : v
}

// 按当前显示单位对方框内 Miller 表排序
const sortedMillerInBox = computed(() => {
  const r = raw.boxResult
  if (!r || !r.miller_in_box) return []
  const key = raw.boxUnit === '2th' ? 'two_theta'
    : raw.boxUnit === 'd' ? 'd_spacing'
    : 'q'
  const list = [...r.miller_in_box]
  if (raw.boxUnit === 'px') return list // px 不排序
  list.sort((a, b) => {
    const av = a[key], bv = b[key]
    if (av == null && bv == null) return 0
    if (av == null) return 1
    if (bv == null) return -1
    return av - bv
  })
  return list
})

// 方框覆盖范围（按当前单位）的展示字符串
const boxCoverageText = computed(() => {
  const r = raw.boxResult
  if (!r || !r.box_coverage) return ''
  const cov = r.box_coverage
  if (raw.boxUnit === '2th' && cov.two_theta) {
    return `2θ: ${cov.two_theta[0]?.toFixed(3)}° – ${cov.two_theta[1]?.toFixed(3)}°`
  }
  if (raw.boxUnit === 'd' && cov.d_spacing) {
    return `d: ${cov.d_spacing[1]?.toFixed(4)} – ${cov.d_spacing[0]?.toFixed(4)} Å`
  }
  if (raw.boxUnit === 'q' && cov.q) {
    return `q: ${cov.q[0]?.toFixed(4)} – ${cov.q[1]?.toFixed(4)} Å⁻¹`
  }
  // px 或缺失：返回像素方框尺寸
  const b = r.box
  if (b) return `px: ${Math.abs(b.x1 - b.x0) + 1} × ${Math.abs(b.y1 - b.y0) + 1}`
  return ''
})

function exportBoxProfileCsv() {
  const r = raw.boxResult
  if (!r) return
  let x
  if (raw.boxUnit === '2th') x = r.two_theta
  else if (raw.boxUnit === 'd') x = r.d_spacing
  else if (raw.boxUnit === 'px') x = r.q_values.map((_, i) => i)
  else x = r.q_values
  const header = raw.boxUnit === '2th' ? '2theta_deg,intensity'
    : raw.boxUnit === 'd' ? 'd_A,intensity'
    : raw.boxUnit === 'px' ? 'bin_index,intensity' : 'q_A-1,intensity'
  const rows = [header]
  for (let i = 0; i < x.length; i++) {
    const xi = x[i] == null ? '' : (typeof x[i] === 'number' ? x[i].toFixed(6) : x[i])
    const yi = r.i_q[i] == null ? '' : r.i_q[i].toFixed(6)
    rows.push(`${xi},${yi}`)
  }
  _downloadText(rows.join('\n'), 'box_profile.csv', 'text/csv')
}

function exportBoxMillerTxt() {
  const r = raw.boxResult
  if (!r || !r.miller_in_box.length) return
  const header = '# h k l  q(A-1)  psi(deg)  2theta(deg)  d(A)  x_px  y_px  intensity  source'
  const rows = r.miller_in_box.map(m =>
    `${m.h} ${m.k} ${m.l}  ${fmt(m.q)} ${fmt(m.psi)} ${fmt(m.two_theta)} ${fmt(m.d_spacing)} ${m.x} ${m.y} ${m.intensity != null ? m.intensity.toFixed(1) : '-'}  ${m.overlay_label || m.overlay_index}`
  )
  _downloadText([header, ...rows].join('\n'), 'box_miller.txt', 'text/plain')
}

function _downloadText(text, filename, mime) {
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
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
  rawReferencePoints: () => fileRawRef.value,
  intReferencePoints: () => fileIntRef.value,
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
      case 'rawReferencePoints': await uploadRawReferencePoints(file); break
      case 'intReferencePoints': await uploadIntReferencePoints(file); break
    }
  } catch(err) {
    setStatus('Error: ' + (err.response?.data?.detail || err.message))
  } finally {
    loading.value = false
  }
}

async function uploadRawImage(file) {
  const name = file.name.toLowerCase()
  if (name.endsWith('.h5') || name.endsWith('.hdf5')) {
    await probeHdf5(file)
    return
  }
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await axios.post(`${API_BASE}/raw/upload-image`, fd)
  applyLoadedImage(data)
  await renderRaw({ preserveView: false })
  emit('raw-session-ready')
  if (effectiveOverlayGroups.value.length) {
    await loadOverlayGroups()
  }
}

// 把"已加载的 2D 图像"响应（upload-image 或 load-hdf5-slice）应用到 raw 状态
function applyLoadedImage(data) {
  raw.imageLoaded = true
  raw.imgW = data.width
  raw.imgH = data.height
  raw.imgMin = Math.floor(data.min)
  raw.imgMax = Math.ceil(data.max)
  raw.p.cmin = Math.floor(data.p01 ?? data.min)
  raw.p.cmax = Math.ceil(data.p99 ?? data.max)
  // 方框积分阈值默认:Max = 前 1% 最强像素的中位数(代表真实强信号,比单一
  // 最亮像素稳健),Min = 0。后端 image_stats 返回 top1pct_median;缺失时
  // 回退 p99 / max。换图时重置为新图的推荐值。
  raw.boxThreshMin = 0
  raw.boxThreshMax = Math.ceil(data.top1pct_median ?? data.p99 ?? data.max)
  raw.fullCount = 0
  raw.outputCount = 0
  raw.refCount = 0
  raw.poniLoaded = false
  setStatus(data.message)
}

async function probeHdf5(file) {
  const fd = new FormData()
  fd.append('file', file)
  try {
    const { data } = await axios.post(`${API_BASE}/raw/probe-hdf5`, fd)
    hdf5Picker.fileKey = data.file_key
    hdf5Picker.filename = data.filename
    hdf5Picker.datasets = data.datasets
    hdf5Picker.open = true
    // 默认选第一个（最大的）dataset，并初始化其额外维为 index=0
    hdf5Picker.selectedPath = data.datasets[0]?.path || ''
    rebuildAxisChoices()
    setStatus(t('visualizer.hdf5SelectPrompt'))
  } catch (err) {
    setStatus('HDF5 probe error: ' + (err.response?.data?.detail || err.message))
    window.$toast?.(t('visualizer.hdf5ProbeFailed') + ': ' + (err.response?.data?.detail || err.message), true)
  }
}

// 根据 selectedPath 对应 dataset 的形状，重建 axisChoices（仅保留额外维，最后两维是 y,x）
function rebuildAxisChoices() {
  const ds = hdf5Picker.datasets.find(d => d.path === hdf5Picker.selectedPath)
  const next = {}
  if (ds) {
    for (let axis = 0; axis < ds.ndim - 2; axis++) {
      // 保留既有选择，否则默认 index=0
      next[axis] = hdf5Picker.axisChoices[axis] || { mode: 'index', index: 0 }
    }
  }
  hdf5Picker.axisChoices = next
}

// 当前选中 dataset 的额外维信息（供模板渲染轴选择器）
const hdf5ExtraAxes = computed(() => {
  const ds = hdf5Picker.datasets.find(d => d.path === hdf5Picker.selectedPath)
  if (!ds) return []
  const axes = []
  for (let axis = 0; axis < ds.ndim - 2; axis++) {
    axes.push({
      axis,
      size: ds.shape[axis],
      choice: hdf5Picker.axisChoices[axis] || { mode: 'index', index: 0 },
    })
  }
  return axes
})

async function loadHdf5Slice() {
  const extraAxes = Object.entries(hdf5Picker.axisChoices).map(
    ([axis, c]) => ({ axis: Number(axis), mode: c.mode, index: c.index ?? 0 })
  )
  try {
    const { data } = await axios.post(`${API_BASE}/raw/load-hdf5-slice`, {
      file_key: hdf5Picker.fileKey,
      dataset_path: hdf5Picker.selectedPath,
      extra_axes: extraAxes,
    })
    applyLoadedImage(data)
    hdf5Picker.open = false
    await renderRaw({ preserveView: false })
    emit('raw-session-ready')
    if (effectiveOverlayGroups.value.length) {
      await loadOverlayGroups()
    }
  } catch (err) {
    setStatus('HDF5 load error: ' + (err.response?.data?.detail || err.message))
    window.$toast?.(t('visualizer.hdf5LoadFailed') + ': ' + (err.response?.data?.detail || err.message), true)
  }
}

function cancelHdf5Picker() {
  hdf5Picker.open = false
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
  await renderRaw({ preserveView: true })
}

async function uploadRawMiller(file, type) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await axios.post(`${API_BASE}/raw/upload-miller?miller_type=${type}`, fd)
  if (type === 'full') raw.fullCount = data.count
  else raw.outputCount = data.count
  setStatus(data.message)
  await renderRaw({ preserveView: true })
}

async function uploadRawReferencePoints(file) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await axios.post(`${API_BASE}/raw/reference-points`, fd)
  raw.refCount = data.count
  setStatus(data.message)
  await renderRaw({ preserveView: true })
}

async function clearRawRef() {
  await axios.delete(`${API_BASE}/raw/reference-points`)
  raw.refCount = 0
  setStatus('Reference points cleared')
  await renderRaw({ preserveView: true })
}

async function clearRawMiller() {
  await axios.delete(`${API_BASE}/raw/miller?miller_type=all`)
  raw.fullCount = 0
  raw.outputCount = 0
  raw.refCount = 0
  setStatus('All markers cleared')
  await renderRaw({ preserveView: true })
}

async function clearRawMillerType(type) {
  await axios.delete(`${API_BASE}/raw/miller?miller_type=${type}`)
  if (type === 'full') raw.fullCount = 0
  else if (type === 'output') raw.outputCount = 0
  setStatus(type === 'full' ? 'FullMiller cleared' : 'outputMiller cleared')
  await renderRaw({ preserveView: true })
}

async function renderRaw({ preserveView = true } = {}) {
  if (!raw.imageLoaded) return
  loading.value = true
  try {
    setPreserveView('raw', preserveView)
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
    raw.fullCount = data.full_miller_count ?? 0
    raw.outputCount = data.output_miller_count ?? 0
    raw.refCount = data.reference_points_count ?? raw.refCount
    const msg = `Rendered | FullMiller: ${data.full_miller_count} pts | outputMiller: ${data.output_miller_count} pts${data.pyfai_used ? ' | pyFAI ✓' : ' | Manual geometry'}`
    setStatus(msg)
    return data.image
  } finally {
    loading.value = false
  }
}

async function applyRawParams() {
  await renderRaw({ preserveView: true })
}

async function refreshRawView() {
  await renderRaw({ preserveView: true })
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
  const image = await renderRaw({ preserveView: true })
  return { image, adjustments: [] }
}

async function saveRawImage() {
  if (!raw.imageSrc) return
  try {
    const { image, adjustments } = await prepareRawExportImage()
    downloadBase64Image(image || raw.imageSrc, 'diffraction_marked.png')
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
  int2d.refCount = 0
  setStatus(data.message)
  await renderInt({ preserveView: false })
  emit('raw-session-ready')
  if (effectiveOverlayGroups.value.length) {
    await loadIntOverlayGroups()
  }
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
  await renderInt({ preserveView: true })
}

async function uploadIntMiller(file, type) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await axios.post(`${API_BASE}/int/upload-miller?miller_type=${type}`, fd)
  if (type === 'full') int2d.fullCount = data.count
  else int2d.outputCount = data.count
  setStatus(data.message)
  await renderInt({ preserveView: true })
}

async function uploadIntReferencePoints(file) {
  const fd = new FormData()
  fd.append('file', file)
  const { data } = await axios.post(`${API_BASE}/int/reference-points`, fd)
  int2d.refCount = data.count
  setStatus(data.message)
  await renderInt({ preserveView: true })
}

async function clearIntRef() {
  await axios.delete(`${API_BASE}/int/reference-points`)
  int2d.refCount = 0
  setStatus('Reference points cleared')
  await renderInt({ preserveView: true })
}

async function clearIntMiller() {
  await axios.delete(`${API_BASE}/int/miller?miller_type=all`)
  int2d.fullCount = 0
  int2d.outputCount = 0
  int2d.refCount = 0
  setStatus('All markers cleared')
  await renderInt({ preserveView: true })
}

async function clearIntMillerType(type) {
  await axios.delete(`${API_BASE}/int/miller?miller_type=${type}`)
  if (type === 'full') int2d.fullCount = 0
  else if (type === 'output') int2d.outputCount = 0
  setStatus(type === 'full' ? 'FullMiller cleared' : 'outputMiller cleared')
  await renderInt({ preserveView: true })
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
  await renderInt({ preserveView: true })
  } catch(err) {
    setStatus('Error: ' + (err.response?.data?.detail || err.message))
  }
}

async function renderInt({ preserveView = true } = {}) {
  if (!int2d.imageLoaded) return
  loading.value = true
  try {
    setPreserveView('int', preserveView)
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
    int2d.fullCount = data.full_miller_count ?? 0
    int2d.outputCount = data.output_miller_count ?? 0
    int2d.refCount = data.reference_points_count ?? int2d.refCount
    const ptsMsg = `FullMiller: ${data.full_miller_count} pts | outputMiller: ${data.output_miller_count} pts${data.reference_points_count != null ? ' | Ref: ' + data.reference_points_count + ' pts' : ''}`
    setStatus(`Rendered | ${ptsMsg}`)
    return data.image
  } finally {
    loading.value = false
  }
}

function debounceRenderInt() {
  clearTimeout(intDebTimer)
  intDebTimer = setTimeout(renderInt, 300)
}

async function prepareIntExportImage() {
  const image = await renderInt({ preserveView: true })
  return { image, adjustments: [] }
}

async function saveIntImage() {
  if (!int2d.imageSrc) return
  try {
    const { image, adjustments } = await prepareIntExportImage()
    downloadBase64Image(image || int2d.imageSrc, '2d_integrated_marked.png')
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
    raw.refCount = data.raw_reference_points ?? 0
    int2d.refCount = data.int_reference_points ?? 0
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
    if (data.full_miller_count !== undefined) raw.fullCount = data.full_miller_count
    if (data.output_miller_count !== undefined) raw.outputCount = data.output_miller_count
    if (props.resultType === 'indexing') {
      if (data.full_miller_content || data.output_miller_content) {
        indexedOverlayGroups.value = [{
            label: 'outputMiller',
            fullMillerContent: data.full_miller_content || '',
            outputMillerContent: data.output_miller_content || '',
            workDir: dir,
            totalReflections: (data.output_miller_count || 0) + (data.full_miller_count || 0),
          }]
      } else {
        indexedOverlayGroups.value = []
      }
    }
    if (data.poni) {
      raw.poniLoaded = true
      raw.p.wl = data.poni.wl || raw.p.wl
      raw.p.px = data.poni.px || raw.p.px
      raw.p.py = data.poni.py || raw.p.py
      raw.p.cx = data.poni.cx || raw.p.cx
      raw.p.cy = data.poni.cy || raw.p.cy
      raw.p.dist = data.poni.dist || raw.p.dist
    }
    if (data.image_loaded) {
      raw.imageLoaded = true
      raw.imgW = data.width || 0
      raw.imgH = data.height || 0
      raw.imgMin = Math.floor(data.min || 0)
      raw.imgMax = Math.ceil(data.max || 65535)
      raw.p.cmin = Math.floor(data.p01 ?? data.min ?? 0)
      raw.p.cmax = Math.ceil(data.p99 ?? data.max ?? 65535)
      await renderRaw({ preserveView: false })
      if (props.resultType === 'indexing') {
        if (indexedOverlayGroups.value.length) {
          await loadOverlayGroups()
        }
      }
      setStatus(data.message || `Loaded from workDir: ${dir}`)
      emit('raw-session-ready')
    } else {
      setStatus(data.message || `Markers preloaded from workDir: ${dir}. Import an image to render them.`)
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
  if (!effectiveOverlayGroups.value || effectiveOverlayGroups.value.length === 0) return
  if (!raw.imageLoaded) return
  loading.value = true
  try {
    const groups = effectiveOverlayGroups.value.slice(0, 5).map(g => ({
      label: g.label || '',
      full_miller_content: g.fullMillerContent || '',
      output_miller_content: g.outputMillerContent || '',
    }))
    const { data } = await axios.post(`${API_BASE}/raw/set-miller-content`, { groups })
    raw.fullCount = data.full_miller_count ?? 0
    raw.outputCount = data.output_miller_count ?? raw.outputCount
    setStatus(data.message || `Overlay: ${groups.length} group(s) loaded`)
    await renderRaw({ preserveView: true })
  } catch (err) {
    setStatus('Error loading overlay groups: ' + (err.response?.data?.detail || err.message))
  } finally {
    loading.value = false
  }
}

async function loadIntOverlayGroups() {
  if (!effectiveOverlayGroups.value || effectiveOverlayGroups.value.length === 0) return
  if (!int2d.imageLoaded) return
  loading.value = true
  try {
    const groups = effectiveOverlayGroups.value.slice(0, 5).map(g => ({
      label: g.label || '',
      full_miller_content: g.fullMillerContent || '',
      output_miller_content: g.outputMillerContent || '',
    }))
    const { data } = await axios.post(`${API_BASE}/int/set-miller-content`, { groups })
    int2d.fullCount = data.full_miller_count ?? 0
    int2d.outputCount = data.output_miller_count ?? int2d.outputCount
    setStatus(data.message || `2D overlay: ${groups.length} group(s) loaded`)
    await renderInt({ preserveView: true })
  } catch (err) {
    setStatus('Error loading 2D overlay groups: ' + (err.response?.data?.detail || err.message))
  } finally {
    loading.value = false
  }
}

watch(() => props.importRequestKey, async (newKey, oldKey) => {
  if (!newKey || newKey === oldKey) return
  const canLoadRaw = raw.imageLoaded
  const canLoadInt = int2d.imageLoaded
  if (!canLoadRaw && !canLoadInt) {
    setStatus('Please import a diffraction or 2D integrated image before loading FullMiller markers')
    return
  }
  if (canLoadRaw) {
    await loadOverlayGroups()
  }
  if (canLoadInt) {
    await loadIntOverlayGroups()
  }
})

watch(() => props.workDir, async (newDir, oldDir) => {
  if (!newDir || newDir === oldDir || props.resultType !== 'indexing') return
  indexedOverlayGroups.value = []
})

// 图像尺寸变化或方框模式开启时，重设叠加层 canvas 尺寸并重画方框
watch(() => [raw.imgW, raw.imgH, raw.boxMode, raw.box, raw.boxDrawing], () => {
  if (raw.boxMode) nextTick(() => drawOverlay())
}, { deep: true })

// HDF5 选择器切换 dataset 时重建额外维选择
watch(() => hdf5Picker.selectedPath, () => rebuildAxisChoices())

onBeforeUnmount(() => {
  Object.values(resetZoomTimers).forEach(timer => {
    if (timer) {
      clearTimeout(timer)
    }
  })
})
</script>

<style scoped>
.visualizer {
  height: calc(100vh - var(--header-height) - 48px);
  display: flex;
  flex-direction: column;
  position: relative;
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

.btn-gold {
  background: rgba(212, 175, 55, 0.12);
  color: #b8860b;
}

.btn-gold:hover {
  background: #d4a017;
  color: var(--text-inverse);
}

.btn-gold:active {
  background: #b8860b;
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

.lbl-ref {
  font: italic 11px var(--font-sans);
  color: #b8860b;
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

.leg-gold {
  color: #b8860b;
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

.overlay-canvas {
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: 0 0;
  pointer-events: auto;
  cursor: crosshair;
  z-index: 10;
  /* 关键:与 <img> 受全局 `img { max-width:100%; height:auto }`(global.css)
     完全一致的尺寸约束。否则 <img> 会被 max-width 限到容器宽,而 canvas
     按 width 属性(natural 像素)布局,二者 layout 尺寸不同 → 经同一
     transform 缩放后不重合 → 方框/光标相对图像偏移。 */
  max-width: 100%;
  height: auto;
}

.box-hint {
  font-size: 12px;
  color: var(--primary, #2563eb);
  background: rgba(37, 99, 235, 0.08);
  border-radius: 4px;
  padding: 4px 6px;
  margin: 6px 0;
}

.box-info {
  font-size: 12px;
  color: var(--text-muted, #6b7280);
  margin-top: 4px;
}

.box-hint-pan {
  color: var(--text-muted, #6b7280);
  background: rgba(107, 114, 128, 0.08);
  margin-top: 4px;
}

.box-thresh {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--border, #e5e7eb);
}

.box-thresh-title {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text, #111);
  margin-bottom: 4px;
}

.box-thresh .form-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  font-size: 12px;
}

.box-thresh .form-row label {
  min-width: 36px;
  color: var(--text-muted, #6b7280);
}

.box-thresh .form-row input {
  flex: 1;
  padding: 2px 6px;
  border: 1px solid var(--border, #d1d5db);
  border-radius: 4px;
  font-size: 12px;
}

.box-result-panel {
  flex: 0 0 auto;
  max-height: 45%;
  overflow-y: auto;
  background: var(--card-bg, #fff);
  border-top: 1px solid var(--border, #e5e7eb);
  padding: 10px 12px;
}

.box-result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.box-result-title {
  font-weight: 600;
  font-size: 13px;
  color: var(--text, #111);
}

.box-xaxis-switch {
  display: flex;
  gap: 10px;
  font-size: 12px;
}

.box-xaxis-switch label {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  cursor: pointer;
}

.box-chart {
  width: 100%;
  margin-top: 4px;
}

.box-miller-table-wrap {
  overflow: auto;
  max-height: 220px;
  margin-top: 4px;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 4px;
}

.box-miller-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  font-family: monospace;
}

.box-miller-table th,
.box-miller-table td {
  padding: 3px 8px;
  border-bottom: 1px solid var(--border, #e5e7eb);
  text-align: right;
  white-space: nowrap;
}

.box-miller-table th {
  background: var(--bg-alt, #f3f4f6);
  position: sticky;
  top: 0;
  z-index: 1;
}

.box-miller-table tr:hover td {
  background: rgba(37, 99, 235, 0.05);
}

.btn-small {
  font-size: 11px;
  padding: 2px 8px;
  margin-left: auto;
}

/* —— 单位选择 / 方框覆盖 —— */
.box-unit-label {
  font-size: 12px;
  color: var(--text-muted, #6b7280);
  margin-right: 4px;
}

.box-coverage {
  font-size: 12px;
  color: var(--primary, #2563eb);
  background: rgba(37, 99, 235, 0.06);
  border-radius: 4px;
  padding: 4px 8px;
  margin-top: 4px;
  font-family: monospace;
}

/* —— HDF5 dataset/切片选择面板 —— */
.hdf5-picker-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
}

.hdf5-picker-card {
  background: var(--card-bg, #fff);
  border-radius: 8px;
  padding: 18px 20px;
  width: min(560px, 92%);
  max-height: 80%;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
}

.hdf5-picker-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 12px;
  display: flex;
  gap: 8px;
  align-items: baseline;
}

.hdf5-picker-filename {
  font-weight: 400;
  font-size: 12px;
  color: var(--text-muted, #6b7280);
  font-family: monospace;
}

.hdf5-picker-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.hdf5-label {
  font-size: 13px;
  min-width: 60px;
  color: var(--text, #111);
}

.hdf5-select {
  flex: 1;
  padding: 4px 6px;
  border: 1px solid var(--border, #d1d5db);
  border-radius: 4px;
  font-size: 12px;
  font-family: monospace;
  background: #fff;
}

.hdf5-info {
  font-size: 12px;
  color: var(--text-muted, #6b7280);
  margin: 4px 0 12px;
}

.hdf5-axis-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.hdf5-axis-label {
  font-size: 12px;
  min-width: 130px;
  color: var(--text, #111);
}

.hdf5-axis-mode {
  flex: 0 0 110px;
}

.hdf5-axis-index {
  width: 80px;
  padding: 3px 6px;
  border: 1px solid var(--border, #d1d5db);
  border-radius: 4px;
  font-size: 12px;
}

.hdf5-projection-hint {
  font-size: 11px;
  color: var(--text-muted, #6b7280);
  font-style: italic;
}

.hdf5-picker-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 14px;
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
  min-width: 0;
}

.visualizer.compact-mode .status-bar {
  padding: 2px 8px;
  font-size: 11px;
}

.visualizer.compact-mode .sidebar {
  width: clamp(240px, 28vw, 280px);
  min-width: 240px;
}

.visualizer.compact-mode .right-panel {
  min-width: 0;
}

.visualizer.compact-mode .image-toolbar {
  padding: 3px 8px;
  font-size: 11px;
  flex-wrap: wrap;
}

.visualizer.compact-mode .image-toolbar .btn {
  padding: 2px 8px;
  font-size: 10px;
}
</style>
