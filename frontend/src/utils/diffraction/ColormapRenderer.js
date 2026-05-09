/**
 * ColormapRenderer - Color mapping for diffraction images
 * 
 * Supports Linear/Log modes and 4 colormaps:
 * - Grayscale
 * - Inverted Grayscale
 * - Heatmap
 * - Rainbow
 */

export const ColormapRenderer = {
  GRayscale: 'grayscale',
  GRayscale_INVERTED: 'grayscale_r',
  HEAT: 'hot',
  JET: 'jet',

  /**
   * Convert image data to RGB array for canvas rendering
   * @param {Array} data - 2D array of intensity values
   * @param {number} min - Minimum intensity
   * @param {number} max - Maximum intensity
   * @param {string} mode - 'Linear' or 'Log'
   * @param {string} colormap - '灰度', '反转灰度', '热力图', '彩虹'
   * @returns {Array} 2D array of [r, g, b] values
   */
  toRGBArray(data, min, max, mode = 'Linear', colormap = '灰度') {
    const height = data.length
    const width = data[0]?.length || 0
    const result = new Array(height)
    
    const span = max - min + 1e-10
    
    for (let i = 0; i < height; i++) {
      result[i] = new Array(width)
      for (let j = 0; j < width; j++) {
        let norm = (data[i][j] - min) / span
        norm = Math.max(0, Math.min(1, norm))
        
        if (mode === 'Log') {
          const v = data[i][j] < 0.1 ? 0.1 : data[i][j]
          norm = Math.log10(v)
          const logMin = Math.log10(Math.max(min, 0.1))
          const logMax = Math.log10(max)
          norm = (norm - logMin) / (logMax - logMin + 1e-10)
          norm = Math.max(0, Math.min(1, norm))
        }
        
        result[i][j] = this.applyColormap(norm, colormap)
      }
    }
    
    return result
  },

  /**
   * Apply colormap to normalized value
   * @param {number} v - Normalized value [0, 1]
   * @param {string} colormap
   * @returns {Array} [r, g, b]
   */
  applyColormap(v, colormap) {
    switch (colormap) {
      case '反转灰度':
        return [Math.round(255 * (1 - v)), Math.round(255 * (1 - v)), Math.round(255 * (1 - v))]
      
      case '热力图':
        return [
          Math.round(255 * v),
          Math.round(128 * (1 - v)),
          Math.round(255 * (1 - v))
        ]
      
      case '彩虹':
        if (v < 0.25) {
          return [0, Math.round(1020 * v), 255]
        } else if (v < 0.5) {
          return [0, 255, Math.round(255 - 1020 * (v - 0.25))]
        } else if (v < 0.75) {
          return [Math.round(1020 * (v - 0.5)), 255, 0]
        } else {
          return [255, Math.round(255 - 1020 * (v - 0.75)), 0]
        }
      
      case '灰度':
      default:
        const g = Math.round(255 * v)
        return [g, g, g]
    }
  },

  /**
   * Create ImageData from 2D array for canvas
   * @param {Array} data - 2D array
   * @param {number} min
   * @param {number} max
   * @param {string} mode
   * @param {string} colormap
   * @returns {ImageData}
   */
  toImageData(data, min, max, mode = 'Linear', colormap = '灰度') {
    const height = data.length
    const width = data[0]?.length || 0
    const rgbArray = this.toRGBArray(data, min, max, mode, colormap)
    
    const imgData = new ImageData(width, height)
    
    for (let i = 0; i < height; i++) {
      for (let j = 0; j < width; j++) {
        const idx = (i * width + j) * 4
        const [r, g, b] = rgbArray[i][j]
        imgData.data[idx] = r
        imgData.data[idx + 1] = g
        imgData.data[idx + 2] = b
        imgData.data[idx + 3] = 255
      }
    }
    
    return imgData
  },

  /**
   * Get plotly colorscale string
   * @param {string} colormap
   * @returns {Array}
   */
  getPlotlyColorscale(colormap) {
    switch (colormap) {
      case '反转灰度':
        return [[0, 'rgb(255,255,255)'], [1, 'rgb(0,0,0)']]
      case '热力图':
        return [[0, 'rgb(0,0,255)'], [0.5, 'rgb(128,128,255)'], [1, 'rgb(255,0,0)']]
      case '彩虹':
        return 'Portland'
      case '灰度':
      default:
        return [[0, 'rgb(0,0,0)'], [1, 'rgb(255,255,255)']]
    }
  }
}

export default ColormapRenderer
