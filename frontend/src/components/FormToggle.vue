<template>
  <label :class="['form-toggle', `form-toggle-${tone}`, { 'is-disabled': disabled }]">
    <input
      :checked="modelValue"
      :disabled="disabled"
      type="checkbox"
      @change="emit('update:modelValue', $event.target.checked)"
    />
    <span class="form-toggle-copy">
      <span class="form-toggle-label">{{ modelValue ? onText : offText }}</span>
    </span>
    <span class="form-toggle-track" aria-hidden="true">
      <span class="form-toggle-thumb"></span>
    </span>
  </label>
</template>

<script setup>
defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  onText: {
    type: String,
    required: true,
  },
  offText: {
    type: String,
    required: true,
  },
  tone: {
    type: String,
    default: 'primary',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue'])
</script>

<style scoped>
.form-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 52px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--bg-primary);
  cursor: pointer;
  transition: border-color var(--transition-fast), background var(--transition-fast), box-shadow var(--transition-fast);
}

.form-toggle:hover {
  border-color: var(--border-hover);
}

.form-toggle input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.form-toggle:has(input:focus-visible) {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.form-toggle.is-disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.form-toggle-copy {
  flex: 1;
  min-width: 0;
}

.form-toggle-label {
  display: block;
  font-size: 0.875rem;
  line-height: 1.4;
  color: var(--text-primary);
  font-weight: 500;
}

.form-toggle-track {
  position: relative;
  width: 44px;
  height: 24px;
  flex-shrink: 0;
  border-radius: 999px;
  background: var(--border);
  transition: background var(--transition-fast);
}

.form-toggle-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.18);
  transition: transform var(--transition-fast);
}

.form-toggle:has(input:checked) .form-toggle-thumb {
  transform: translateX(20px);
}

.form-toggle-primary {
  background: rgba(59, 130, 246, 0.04);
}

.form-toggle-primary:has(input:checked) {
  border-color: rgba(59, 130, 246, 0.32);
  background: rgba(59, 130, 246, 0.08);
}

.form-toggle-primary:has(input:checked) .form-toggle-track {
  background: var(--primary-light);
}

.form-toggle-success {
  background: rgba(16, 185, 129, 0.04);
}

.form-toggle-success:has(input:checked) {
  border-color: rgba(16, 185, 129, 0.32);
  background: rgba(16, 185, 129, 0.08);
}

.form-toggle-success:has(input:checked) .form-toggle-track {
  background: var(--status-success);
}
</style>
