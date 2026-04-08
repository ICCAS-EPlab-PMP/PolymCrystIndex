<template>
  <div class="data-import">
    <div class="page-header">
      <h2>{{ t('dataImport.title') }}</h2>
      <p>{{ t('dataImport.subtitle') }}</p>
    </div>

    <div class="upload-section">
      <div
        class="drop-zone"
        :class="{ dragging: isDragging, 'has-file': uploadedFile }"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="handleDrop"
        @click="triggerFileInput"
      >
        <input
          ref="fileInput"
          type="file"
          accept=".txt"
          @change="handleFileSelect"
          hidden
        />

        <div v-if="!uploadedFile" class="drop-content">
          <div class="upload-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
              <polyline points="17,8 12,3 7,8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
          </div>
          <h3>{{ t('dataImport.dropHere') }}</h3>
          <p>{{ t('dataImport.orBrowse') }} <span class="link">{{ t('dataImport.browse') }}</span></p>
          <div class="file-format">
            <span class="format-badge">{{ t('dataImport.format') }}</span>
            <span class="format-info">{{ t('dataImport.formatInfo') }}</span>
          </div>
        </div>

        <div v-else class="file-info">
          <div class="file-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10,9 9,9 8,9"/>
            </svg>
          </div>
          <div class="file-details">
            <span class="file-name">{{ uploadedFile.name }}</span>
            <span class="file-size">{{ formatFileSize(uploadedFile.size) }}</span>
          </div>
          <button class="btn-remove" @click.stop="removeFile">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
      </div>

      <div v-if="validationResult" class="validation-result" :class="validationResult.data?.valid ? 'success' : 'error'">
        <div class="result-icon">
          <svg v-if="validationResult?.data?.valid" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
            <polyline points="22,4 12,14.01 9,11.01"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
        </div>
        <div class="result-content">
          <span class="result-title">{{ validationResult?.data?.valid ? t('dataImport.validFile') : t('dataImport.invalidFile') }}</span>
          <span class="result-message">{{ validationResult.message }}</span>
          <span v-if="validationResult?.data?.valid" class="result-count">{{ validationResult?.data?.count }} {{ t('dataImport.dataPoints') }}</span>
        </div>
      </div>

      <div v-if="validationResult?.data?.valid && dataPreview.length > 0" class="data-preview">
        <h4>{{ t('dataImport.dataPreview') || 'Data Preview' }}</h4>
        <div class="preview-table-wrapper">
          <table class="preview-table">
            <thead>
              <tr>
                <th>#</th>
                <th>q (Å⁻¹)</th>
                <th>ψ (°)</th>
                <th>Contribution</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, index) in dataPreview" :key="index">
                <td>{{ index + 1 }}</td>
                <td>{{ row.q }}</td>
                <td>{{ row.psi }}</td>
                <td>{{ row.contribution }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="preview-hint" v-if="validationResult?.data?.count > 10">... and {{ validationResult?.data?.count - 10 }} more rows</p>
      </div>
    </div>

    <div class="info-cards">
      <div class="info-card">
        <div class="card-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <path d="M12 16v-4"/>
            <path d="M12 8h.01"/>
          </svg>
        </div>
        <div class="card-content">
          <h4>{{ t('dataImport.fileFormat') }}</h4>
          <p>{{ t('dataImport.fileFormatDesc') }}</p>
          <code>{{ t('dataImport.codeExample') }}</code>
          <ul>
            <li><strong>{{ t('dataImport.qLabel') }}</strong> {{ t('dataImport.qDesc') }}</li>
            <li><strong>{{ t('dataImport.psiLabel') }}</strong> {{ t('dataImport.psiDesc') }}</li>
            <li><strong>{{ t('dataImport.intensityLabel') }}</strong> {{ t('dataImport.intensityDesc') }}</li>
          </ul>
        </div>
      </div>

      <div class="info-card">
        <div class="card-icon warning">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </div>
        <div class="card-content">
          <h4>{{ t('dataImport.preprocessing') }}</h4>
          <p>{{ t('dataImport.preprocessingDesc') }}</p>
          <ul>
            <li>{{ t('dataImport.pre1') }}</li>
            <li>{{ t('dataImport.pre2') }}</li>
            <li>{{ t('dataImport.pre3') }}</li>
          </ul>
        </div>
      </div>
    </div>

    <div class="actions">
      <button class="btn-primary" :disabled="!uploadedFile || !validationResult?.data?.valid || !uploadedFilePath" @click="proceedToParams">
        {{ t('dataImport.continue') }}
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="5" y1="12" x2="19" y2="12"/>
          <polyline points="12,5 19,12 12,19"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '@/api/index'

const { t } = useI18n()
const props = defineProps({
  uploadedFileData: {
    type: Object,
    default: null
  }
})
const emit = defineEmits(['data-loaded', 'file-removed'])

const fileInput = ref(null)
const isDragging = ref(false)
const uploadedFile = ref(null)
const fileContent = ref('')
const validationResult = ref(null)
const uploadedFilePath = ref(null)
const dataPreview = ref([])

onMounted(() => {
  if (props.uploadedFileData?.path) {
    uploadedFilePath.value = props.uploadedFileData.path
    validationResult.value = { data: { valid: true }, success: true }
    if (props.uploadedFileData.file) {
      uploadedFile.value = props.uploadedFileData.file
      if (props.uploadedFileData.content) {
        fileContent.value = props.uploadedFileData.content
        parseDataPreview(props.uploadedFileData.content)
      }
    }
  }
})

const triggerFileInput = () => {
  fileInput.value?.click()
}

const handleFileSelect = async (event) => {
  const file = event.target.files[0]
  if (file) {
    await processFile(file)
  }
}

const handleDrop = async (event) => {
  isDragging.value = false
  const file = event.dataTransfer.files[0]
  if (file && file.name.endsWith('.txt')) {
    await processFile(file)
  }
}

const processFile = async (file) => {
  uploadedFile.value = file
  fileContent.value = ''
  dataPreview.value = []
  uploadedFilePath.value = null
  
  const reader = new FileReader()
  reader.onload = async (e) => {
    const content = e.target.result
    fileContent.value = content
    parseDataPreview(content)
    
    try {
      validationResult.value = await api.checkData(content)
      if (validationResult.value.success && validationResult.value.data.valid) {
        const uploadResult = await api.uploadData(file)
        if (uploadResult.success) {
          uploadedFilePath.value = uploadResult.data.path
        }
      } else {
        validationResult.value = {
          valid: validationResult.value.data?.valid || false,
          message: validationResult.value.message || 'Validation failed',
          count: validationResult.value.data?.count || 0
        }
      }
    } catch (error) {
      validationResult.value = {
        valid: false,
        message: error.message || 'Validation failed'
      }
    }
  }
  reader.readAsText(file)
}

const parseDataPreview = (content) => {
  const lines = content.trim().split('\n').slice(0, 10)
  dataPreview.value = []
  for (const line of lines) {
    const parts = line.trim().split(/\s+/)
    if (parts.length >= 3) {
      const q = parseFloat(parts[0])
      const psi = parseFloat(parts[1])
      const contribution = parseFloat(parts[2])
      if (!isNaN(q) && !isNaN(psi) && !isNaN(contribution)) {
        dataPreview.value.push({ q, psi, contribution })
      }
    }
  }
}

const removeFile = () => {
  uploadedFile.value = null
  fileContent.value = ''
  dataPreview.value = []
  validationResult.value = null
  uploadedFilePath.value = null
  if (fileInput.value) {
    fileInput.value.value = ''
  }
  emit('file-removed')
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const proceedToParams = () => {
  if (uploadedFile.value && validationResult.value?.data?.valid && uploadedFilePath.value) {
    emit('data-loaded', { file: uploadedFile.value, path: uploadedFilePath.value, content: fileContent.value })
  } else if (uploadedFile.value && validationResult.value?.data?.valid) {
    alert('Please wait for file upload to complete')
  }
}
</script>

<style scoped>
.data-import {
  max-width: 900px;
}

.page-header {
  margin-bottom: 32px;
}

.page-header h2 {
  font-size: 1.75rem;
  margin-bottom: 8px;
}

.page-header p {
  color: var(--text-secondary);
}

.upload-section {
  margin-bottom: 32px;
}

.drop-zone {
  border: 2px dashed var(--border);
  border-radius: var(--radius-lg);
  padding: 48px;
  text-align: center;
  cursor: pointer;
  transition: all var(--transition-normal);
  background: var(--bg-surface);
}

.drop-zone:hover {
  border-color: var(--primary-light);
  background: var(--bg-hover);
}

.drop-zone.dragging {
  border-color: var(--primary);
  background: var(--primary-bg);
}

.drop-zone.has-file {
  padding: 24px;
  cursor: default;
}

.drop-content .upload-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 20px;
  color: var(--primary-light);
}

.drop-content .upload-icon svg {
  width: 100%;
  height: 100%;
}

.drop-content h3 {
  font-size: 1.25rem;
  margin-bottom: 8px;
}

.drop-content p {
  color: var(--text-secondary);
  margin-bottom: 16px;
}

.drop-content .link {
  color: var(--primary);
  font-weight: 500;
}

.file-format {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}

.format-badge {
  background: var(--bg-surface-alt);
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  font-family: 'Fira Code', monospace;
  color: var(--text-secondary);
}

.format-info {
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.file-info {
  display: flex;
  align-items: center;
  gap: 16px;
  text-align: left;
}

.file-icon {
  width: 48px;
  height: 48px;
  color: var(--primary);
}

.file-icon svg {
  width: 100%;
  height: 100%;
}

.file-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.file-name {
  font-weight: 600;
  color: var(--text-primary);
}

.file-size {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.btn-remove {
  width: 36px;
  height: 36px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--bg-surface-alt);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-remove:hover {
  background: var(--error-light);
  color: var(--error);
}

.btn-remove svg {
  width: 18px;
  height: 18px;
}

.validation-result {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-top: 20px;
  padding: 16px 20px;
  border-radius: var(--radius-md);
}

.validation-result.success {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid var(--secondary);
}

.validation-result.error {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--error-light);
}

.result-icon {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
}

.result-icon svg {
  width: 100%;
  height: 100%;
}

.validation-result.success .result-icon {
  color: var(--secondary);
}

.validation-result.error .result-icon {
  color: var(--error);
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.result-title {
  font-weight: 600;
}

.validation-result.success .result-title {
  color: var(--secondary);
}

.validation-result.error .result-title {
  color: var(--error);
}

.result-message {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.result-count {
  font-size: 0.8125rem;
  font-family: 'Fira Code', monospace;
  color: var(--text-muted);
}

.info-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
  margin-bottom: 32px;
}

.info-card {
  display: flex;
  gap: 16px;
  padding: 20px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}

.card-icon {
  width: 40px;
  height: 40px;
  padding: 8px;
  border-radius: var(--radius-md);
  background: var(--primary-bg);
  color: var(--primary);
  flex-shrink: 0;
}

.card-icon.warning {
  background: rgba(245, 158, 11, 0.1);
  color: var(--cta);
}

.card-icon svg {
  width: 100%;
  height: 100%;
}

.card-content h4 {
  font-size: 1rem;
  margin-bottom: 8px;
}

.card-content p {
  font-size: 0.875rem;
  margin-bottom: 8px;
}

.card-content code {
  display: block;
  padding: 8px 12px;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-sm);
  font-size: 0.8125rem;
  margin-bottom: 12px;
}

.card-content ul {
  list-style: none;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.card-content li {
  padding: 4px 0;
  padding-left: 16px;
  position: relative;
}

.card-content li::before {
  content: '•';
  position: absolute;
  left: 0;
  color: var(--text-muted);
}

.card-content li strong {
  color: var(--text-primary);
}

.data-preview {
  margin-top: 20px;
  padding: 16px 20px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
}

.data-preview h4 {
  font-size: 0.9375rem;
  margin-bottom: 12px;
  color: var(--text-primary);
}

.preview-table-wrapper {
  overflow-x: auto;
}

.preview-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
  font-family: 'Fira Code', monospace;
}

.preview-table th,
.preview-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid var(--border);
}

.preview-table th {
  background: var(--bg-surface-alt);
  font-weight: 600;
  color: var(--text-secondary);
}

.preview-table td {
  color: var(--text-primary);
}

.preview-hint {
  margin-top: 8px;
  font-size: 0.75rem;
  color: var(--text-muted);
}

.actions {
  display: flex;
  justify-content: flex-end;
}

.btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.btn-primary:hover:not(:disabled) {
  background: var(--primary-dark);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary svg {
  width: 18px;
  height: 18px;
}
</style>
