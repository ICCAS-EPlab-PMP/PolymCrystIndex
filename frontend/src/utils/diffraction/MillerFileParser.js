/**
 * MillerFileParser - Parse FullMiller.txt and outputMiller.txt files
 * 
 * FullMiller.txt format: H K L q(A-1) psi(degree) psi-root(degree) 2theta(degree)
 * outputMiller.txt format: H K L q psi
 */

export class MillerFileParser {
  /**
   * Parse Miller file content
   * @param {string} content - File content
   * @param {string} type - 'full' or 'output'
   * @returns {Array} Array of Miller data points
   */
  static parse(content, type = 'full') {
    const lines = content.trim().split('\n')
    const result = []
    
    for (const line of lines) {
      const trimmed = line.trim()
      if (!trimmed) continue
      
      const parts = trimmed.split(/\s+/)
      
      if (parts.length < 5) continue
      
      if (type === 'full' && parts.length < 7) continue
      
      if (!this.isDataLine(parts[0])) continue
      
      try {
        const h = parseInt(parts[0], 10)
        const k = parseInt(parts[1], 10)
        const l = parseInt(parts[2], 10)
        const q = parseFloat(parts[3])
        const psi = parseFloat(parts[4])
        
        if (isNaN(h) || isNaN(k) || isNaN(l)) continue
        if (isNaN(q) || q <= 0) continue
        
        if (parts[0].match(/^[a-zA-Z]+$/)) continue
        
        const entry = { h, k, l, q, psi }
        
        if (type === 'full') {
          const psiRoot = parseFloat(parts[5])
          entry.psiRoot = isNaN(psiRoot) ? null : psiRoot
          
          if (parts.length >= 7) {
            const twoTheta = parseFloat(parts[6])
            entry.twoTheta = isNaN(twoTheta) ? null : twoTheta
          }
        } else {
          entry.psiRoot = null
          entry.twoTheta = null
        }
        
        result.push(entry)
      } catch (e) {
        console.warn('[MillerFileParser] Failed to parse line:', trimmed)
      }
    }
    
    return result
  }
  
  /**
   * Check if first token is a valid HKL index (numeric)
   */
  static isDataLine(firstToken) {
    if (!firstToken) return false
    const c = firstToken.charAt(0)
    if (c === '-' || c === '+' || (c >= '0' && c <= '9')) {
      const num = parseInt(firstToken, 10)
      return !isNaN(num)
    }
    return false
  }
  
  /**
   * Parse Miller file from file object
   * @param {File} file - File object
   * @param {string} type - 'full' or 'output'
   * @returns {Promise<Array>}
   */
  static async parseFile(file, type = 'full') {
    const content = await file.text()
    return this.parse(content, type)
  }
}

export default MillerFileParser
