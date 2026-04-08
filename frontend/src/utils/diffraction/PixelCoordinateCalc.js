/**
 * PixelCoordinateCalc - Compute pixel coordinates from (q, ψ)
 * 
 * Implements the same geometric calculation as the PySide6 version:
 * - sin(θ) = q * λ / 4π
 * - r_mm = dist * tan(2θ)
 * - Quadrant correction for ψ rotation offset
 * 
 * Quadrant signs:
 *   Q1: sx=+1, sy=-1  → sign_corr = -(sx*sy) = +1 → use +rot_offset
 *   Q2: sx=-1, sy=-1  → sign_corr = -(sx*sy) = +1 → use +rot_offset  
 *   Q3: sx=-1, sy=+1  → sign_corr = -(sx*sy) = +1 → use +rot_offset
 *   Q4: sx=+1, sy=+1  → sign_corr = -(sx*sy) = +1 → use +rot_offset
 */

const QUADRANT_SIGNS = {
  'Quadrant I': { sx: 1, sy: -1 },
  'Quadrant II': { sx: -1, sy: -1 },
  'Quadrant III': { sx: -1, sy: 1 },
  'Quadrant IV': { sx: 1, sy: 1 }
}

export class PixelCoordinateCalc {
  constructor() {
    this._wl = 1.0
    this._px = 100.0
    this._py = 100.0
    this._cx = 0.0
    this._cy = 0.0
    this._dist = 1000.0
    this._quad = 'Quadrant IV'
    this._rotOffset = 0.0
  }

  /**
   * Set wavelength in Angstroms
   */
  setWavelength(wl) {
    this._wl = wl
  }

  /**
   * Set pixel size in micrometers
   */
  setPixelSize(px, py) {
    this._px = px
    this._py = py
  }

  /**
   * Set detector center in pixels
   */
  setCenter(cx, cy) {
    this._cx = cx
    this._cy = cy
  }

  /**
   * Set detector distance in mm
   */
  setDistance(dist) {
    this._dist = dist
  }

  /**
   * Set quadrant
   * @param {string} quad - 'Quadrant I', 'II', 'III', or 'IV'
   */
  setQuadrant(quad) {
    this._quad = quad
  }

  /**
   * Set ψ rotation offset in degrees
   */
  setRotOffset(rot) {
    this._rotOffset = rot
  }

  /**
   * Update all parameters at once
   * @param {Object} params
   */
  setParams(params) {
    if (params.wavelength !== undefined) this._wl = params.wavelength
    if (params.px !== undefined) this._px = params.px
    if (params.py !== undefined) this._py = params.py
    if (params.cx !== undefined) this._cx = params.cx
    if (params.cy !== undefined) this._cy = params.cy
    if (params.dist !== undefined) this._dist = params.dist
    if (params.quad !== undefined) this._quad = params.quad
    if (params.rot !== undefined) this._rotOffset = params.rot
  }

  /**
   * Compute pixel coordinates for a single (q, ψ) point
   * @param {number} q - q value in Å⁻¹
   * @param {number} psi - ψ angle in degrees
   * @returns {{x: number, y: number}}
   */
  compute(q, psi) {
    const signs = QUADRANT_SIGNS[this._quad] || QUADRANT_SIGNS['Quadrant IV']
    const { sx, sy } = signs
    
    const signCorr = -(sx * sy)
    const effPsi = psi + this._rotOffset * signCorr
    
    try {
      const sinTheta = (q * this._wl) / (4.0 * Math.PI)
      
      if (Math.abs(sinTheta) > 1.0) {
        return { x: 0, y: 0 }
      }
      
      const theta = Math.asin(sinTheta)
      const rMm = this._dist * Math.tan(2.0 * theta)
      
      const psiRad = effPsi * Math.PI / 180
      
      const x = this._cx + (sx * rMm * Math.cos(psiRad) * 1000.0) / this._px
      const y = this._cy + (sy * rMm * Math.sin(psiRad) * 1000.0) / this._py
      
      return {
        x: Math.round(x),
        y: Math.round(y)
      }
    } catch (e) {
      return { x: 0, y: 0 }
    }
  }

  /**
   * Compute pixel coordinates for multiple Miller points
   * @param {Array} millerData - Array of {h, k, l, q, psi, ...}
   * @returns {Array} Array of {h, k, l, q, psi, x, y, ...}
   */
  computeBatch(millerData) {
    return millerData.map(m => {
      const { x, y } = this.compute(m.q, m.psi)
      return { ...m, x, y }
    })
  }
}

/**
 * Normalize angle to (-180, 180]
 */
export function normalizeAngle(angle) {
  let a = angle % 360
  if (a < 0) a += 360
  if (a >= 180) a -= 360
  return a
}

/**
 * Psi to Azimuth mapper for 2D integration images
 */
export class PsiAzimuthMapper {
  constructor(convention = 'ccw', offset = 0) {
    this.convention = convention
    this.offset = offset
  }

  /**
   * Map psi to azimuth angle
   * @param {number} psi
   * @returns {number}
   */
  map(psi) {
    let az
    if (this.convention === 'ccw') {
      az = -psi + this.offset
    } else {
      az = psi + this.offset
    }
    return normalizeAngle(az)
  }

  /**
   * Map a list of Miller data
   * @param {Array} millerData
   * @returns {Array}
   */
  mapBatch(millerData) {
    return millerData.map(m => ({
      q: m.q,
      az: this.map(m.psi),
      hkl: `(${m.h},${m.k},${m.l})`,
      h: m.h,
      k: m.k,
      l: m.l,
      psi: m.psi,
      psiRoot: m.psiRoot
    }))
  }
}

export default PixelCoordinateCalc
