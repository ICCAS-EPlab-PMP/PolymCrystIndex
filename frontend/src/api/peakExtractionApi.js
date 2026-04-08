import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120_000,
})

export const rawApi = {
  load:          (file)    => { const f = new FormData(); f.append('file', file); return api.post('/peak/raw/load', f) },
  importPoni:    (file)    => { const f = new FormData(); f.append('file', file); return api.post('/peak/raw/import-poni', f) },
  render:        (body)    => api.post('/peak/raw/render', body),
  applyThresh:   (body)    => api.post('/peak/raw/apply-threshold', body),
  click:         (body)    => api.post('/peak/raw/click', body),
  zoomClick:     (body)    => api.post('/peak/raw/zoom-click', body),
  integrate:     (body)    => api.post('/peak/raw/integrate', body),
  recordPoint:   (body)    => api.post('/peak/raw/record-point', body),
  deleteRecord:  (body)    => api.post('/peak/raw/delete-record', body),
  clearRecords:  (sid)     => api.post('/peak/raw/clear-records', { session_id: sid }),
  calcPixel:     (body)    => api.post('/peak/raw/calc-pixel', body),
  exportCsv:     (sid)     => `/api/peak/raw/export-csv/${sid}`,
}

export const intApi = {
  load:           (file)  => { const f = new FormData(); f.append('file', file); return api.post('/peak/integrated/load', f) },
  importInfo:     (file)  => { const f = new FormData(); f.append('file', file); return api.post('/peak/integrated/import-info', f) },
  importMiller:   (file, sid) => { const f = new FormData(); f.append('file', file); f.append('session_id', sid); return api.post('/peak/integrated/import-miller', f) },
  setRanges:      (body)  => api.post('/peak/integrated/set-ranges', body),
  transformMiller:(body)  => api.post('/peak/integrated/transform-miller', body),
  getSlice:       (body)  => api.post('/peak/integrated/get-slice', body),
  findPeaks:      (body)  => api.post('/peak/integrated/find-peaks', body),
  recordPeaks:    (body)  => api.post('/peak/integrated/record-peaks', body),
  deleteRecord:   (body)  => api.post('/peak/integrated/delete-record', body),
  clearRecords:   (sid)   => api.post('/peak/integrated/clear-records', { session_id: sid }),
  exportCsv:      (sid)   => `/api/peak/integrated/export-csv/${sid}`,
}