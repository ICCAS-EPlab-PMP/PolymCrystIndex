<template>
  <div v-if="visible" class="dialog-overlay" @click.self="handleCancel">
    <div class="dialog" :class="[`dialog-${type}`]">
      <div class="dialog-header">
        <div class="dialog-icon" v-if="type === 'danger'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
        </div>
        <div class="dialog-icon dialog-icon-info" v-else-if="type === 'info'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
        </div>
        <h3>{{ title }}</h3>
      </div>
      <div class="dialog-body">
        <p>{{ message }}</p>
      </div>
      <div class="dialog-footer">
        <button v-if="cancelText" class="btn-secondary" @click="handleCancel">{{ cancelText }}</button>
        <button
          :class="[type === 'danger' ? 'btn-danger' : 'btn-primary']"
          @click="handleConfirm"
        >
          {{ confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: false },
  title: { type: String, default: '' },
  message: { type: String, default: '' },
  confirmText: { type: String, default: 'Confirm' },
  cancelText: { type: String, default: 'Cancel' },
  type: { type: String, default: 'info' },
})

const emit = defineEmits(['confirm', 'cancel'])

const handleConfirm = () => emit('confirm')
const handleCancel = () => emit('cancel')
</script>

<style scoped>
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(2px);
}

.dialog {
  background: var(--bg-surface, #fff);
  border-radius: var(--radius-lg, 12px);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  min-width: 400px;
  max-width: 500px;
  overflow: hidden;
  animation: dialog-enter 0.2s ease-out;
}

@keyframes dialog-enter {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.dialog-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px 0;
}

.dialog-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #fff;
  background: var(--error, #ef4444);
}

.dialog-icon-info {
  background: var(--primary, #3b82f6);
}

.dialog-header h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-primary, #1f2937);
}

.dialog-body {
  padding: 16px 24px;
}

.dialog-body p {
  margin: 0;
  color: var(--text-secondary, #6b7280);
  font-size: 0.9rem;
  line-height: 1.5;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 24px 20px;
}

.btn-secondary {
  padding: 8px 20px;
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--border, #e5e7eb);
  background: var(--bg-surface, #fff);
  color: var(--text-secondary, #6b7280);
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.15s;
}

.btn-secondary:hover {
  background: var(--bg-surface-alt, #f3f4f6);
}

.btn-primary {
  padding: 8px 20px;
  border-radius: var(--radius-md, 8px);
  border: none;
  background: var(--primary, #3b82f6);
  color: #fff;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.15s;
}

.btn-primary:hover {
  filter: brightness(1.1);
}

.btn-danger {
  padding: 8px 20px;
  border-radius: var(--radius-md, 8px);
  border: none;
  background: var(--error, #ef4444);
  color: #fff;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: all 0.15s;
}

.btn-danger:hover {
  filter: brightness(1.1);
}
</style>
