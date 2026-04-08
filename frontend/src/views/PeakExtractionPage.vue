<template>
  <div class="peak-extraction-page">
    <div class="main-container">
      <aside class="sidebar">
        <nav class="tab-nav">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            :class="['tab-item', { active: activeTab === tab.id }]"
            @click="activeTab = tab.id"
          >
            <component :is="tab.icon" class="tab-icon" />
            <span class="tab-label">{{ tab.label }}</span>
          </button>
        </nav>

        <div class="sidebar-footer">
          <div class="status-indicator">
            <span class="status-dot"></span>
            <span class="status-text">{{ statusMsg }}</span>
          </div>
        </div>
      </aside>

      <main class="content">
        <transition name="fade" mode="out-in">
          <RawView v-if="activeTab === 'raw'" @status="setStatus" />
          <IntView v-else-if="activeTab === 'integrated'" @status="setStatus" />
        </transition>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, markRaw, defineAsyncComponent } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const RawView = defineAsyncComponent(() => import('@/components/RawView.vue'))
const IntView = defineAsyncComponent(() => import('@/components/IntView.vue'))

const IconImage = {
  template: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
    <circle cx="8.5" cy="8.5" r="1.5"/>
    <polyline points="21,15 16,10 5,21"/>
  </svg>`
}

const IconChart = {
  template: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <line x1="18" y1="20" x2="18" y2="10"/>
    <line x1="12" y1="20" x2="12" y2="4"/>
    <line x1="6" y1="20" x2="6" y2="14"/>
  </svg>`
}

const tabs = computed(() => [
  { id: 'raw', label: t('peakExtraction.rawImage'), icon: markRaw(IconImage) },
  { id: 'integrated', label: t('peakExtraction.integrated'), icon: markRaw(IconChart) }
])

const activeTab = ref('raw')
const statusMsg = ref(t('peakExtraction.ready'))

function setStatus(msg) {
  statusMsg.value = msg
}

</script>

<style scoped>
.peak-extraction-page {
  display: flex;
  flex-direction: column;
}

.main-container {
  display: flex;
  flex: 1;
}

.sidebar {
  width: var(--sidebar-width);
  background: var(--bg-surface);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: calc(100vh - var(--header-height));
  align-self: flex-start;
}

.tab-nav {
  flex: 1;
  padding: 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tab-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border: none;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.9375rem;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: all var(--transition-fast);
  position: relative;
}

.tab-item:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.tab-item.active {
  background: var(--primary-bg);
  color: var(--primary);
}

.tab-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 24px;
  background: var(--primary);
  border-radius: 0 2px 2px 0;
}

.tab-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.tab-label {
  flex: 1;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid var(--border);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

.status-text {
  color: var(--text-secondary);
}

.content {
  flex: 1;
  padding: 24px;
  max-width: calc(var(--content-max-width) + 48px);
  overflow-x: hidden;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
