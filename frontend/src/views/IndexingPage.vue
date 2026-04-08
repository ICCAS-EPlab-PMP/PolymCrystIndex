<template>
  <div class="indexing-page">
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
            <span class="tab-label">{{ getTabLabel(tab.id) }}</span>
            <span v-if="tab.badge" class="tab-badge">{{ tab.badge }}</span>
          </button>
        </nav>

        <div class="sidebar-footer">
          <div class="status-indicator">
            <span class="status-dot" :class="statusClass"></span>
            <span class="status-text">{{ t(`status.${runStatus}`) }}</span>
          </div>
</div>
      </aside>

      <main class="content">
        <transition name="fade" mode="out-in">
          <DataImport v-if="activeTab === 'data'" :uploaded-file-data="dataFile" @data-loaded="handleDataLoaded" @file-removed="handleFileRemoved" />
          <ParamsSetup v-else-if="activeTab === 'params'" :params="gaParams" />
          <Console v-else-if="activeTab === 'console'" :params="gaParams" :data-file="dataFile" @navigate="handleNavigate" />
          <ResultExport v-else-if="activeTab === 'results'" @navigate="handleNavigate" />
        </transition>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, markRaw, defineAsyncComponent } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const DataImport = defineAsyncComponent(() => import('@/components/DataImport.vue'))
const ParamsSetup = defineAsyncComponent(() => import('@/components/ParamsSetup.vue'))
const Console = defineAsyncComponent(() => import('@/components/Console.vue'))
const ResultExport = defineAsyncComponent(() => import('@/components/ResultExport.vue'))

const IconFileUpload = {
  template: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
    <polyline points="17,8 12,3 7,8"/>
    <line x1="12" y1="3" x2="12" y2="15"/>
  </svg>`
}

const IconSettings = {
  template: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <circle cx="12" cy="12" r="3"/>
    <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-2 2 2 2 0 01-2-2v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83 0 2 2 0 010-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 01-2-2 2 2 0 012-2h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 010-2.83 2 2 0 012.83 0l.06.06a1.65 1.65 0 001.82.33H9a1.65 1.65 0 001-1.51V3a2 2 0 012-2 2 2 0 012 2v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 0 2 2 0 010-2.83l-.06-.06a1.65 1.65 0 00.33-1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 012 2 2 2 0 01-2 2h-.09a1.65 1.65 0 00-1.51 1z"/>
  </svg>`
}

const IconRocket = {
  template: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 00-2.91-.09z"/>
    <path d="M12 15l-3-3a22 22 0 012-3.95A12.88 12.88 0 0122 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 01-4 2z"/>
    <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/>
    <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>
  </svg>`
}

const IconChartBar = {
  template: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <line x1="12" y1="20" x2="12" y2="10"/>
    <line x1="18" y1="20" x2="18" y2="4"/>
    <line x1="6" y1="20" x2="6" y2="16"/>
  </svg>`
}

const IconInfo = {
  template: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <circle cx="12" cy="12" r="10"/>
    <line x1="12" y1="16" x2="12" y2="12"/>
    <line x1="12" y1="8" x2="12.01" y2="8"/>
  </svg>`
}

const tabs = [
  { id: 'data', label: 'Data Import', icon: markRaw(IconFileUpload) },
  { id: 'params', label: 'Parameters', icon: markRaw(IconSettings) },
  { id: 'console', label: 'Analysis', icon: markRaw(IconRocket) },
  { id: 'results', label: 'Results', icon: markRaw(IconChartBar) }
]

const activeTab = ref('data')
const dataFile = ref(null)
const runStatus = ref('idle')

const gaParams = reactive({
  steps: 30,
  generations: 2000,
  liveRatio: 10,
  exchangeRatio: 20,
  mutateRatio: 50,
  newRatio: 20,
  aMin: 3.0,
  aMax: 10.0,
  bMin: 3.0,
  bMax: 10.0,
  cMin: 5.0,
  cMax: 15.0,
  alphaMin: 60,
  alphaMax: 150,
  betaMin: 60,
  betaMax: 150,
  gammaMin: 60,
  gammaMax: 150,
  e1: 1.0,
  e2: 100.0,
  e3: 500.0,
  e4: 1.0,
  wavelength: 1.542,
  esym: 0.95,
  duplicate: false,
  lmMode: true,
  tiltCheck: false,
  pseuOrth: false,
  hklMode: 'Default',
  custH: 5,
  custK: 5,
  custL: 0,
  ompThreads: 1
})

const statusClass = computed(() => runStatus.value)

const getTabLabel = (tabId) => {
  if (tabId === 'data') return t('nav.dataImport')
  if (tabId === 'params') return t('nav.parameters')
  if (tabId === 'console') return t('nav.analysis')
  if (tabId === 'results') return t('nav.results')
  return tabId
}

const handleDataLoaded = (data) => {
  dataFile.value = data
  activeTab.value = 'params'
}

const handleFileRemoved = () => {
  dataFile.value = null
}

const handleNavigate = (tab) => {
  activeTab.value = tab
}

</script>

<style scoped>
.indexing-page {
  display: flex;
  flex-direction: column;
  gap: 0;
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

.tab-badge {
  background: var(--primary);
  color: white;
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 600;
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

.status-dot.running {
  background: var(--status-running);
  animation: pulse 2s infinite;
}

.status-dot.success {
  background: var(--status-success);
}

.status-dot.error {
  background: var(--status-error);
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

@media (max-width: 1024px) {
  .sidebar {
    width: var(--sidebar-collapsed);
  }

  .tab-label,
  .tab-badge,
  .sidebar-footer {
    display: none;
  }

  .tab-item {
    justify-content: center;
    padding: 12px;
  }

  .tab-item.active::before {
    display: none;
  }
}

</style>
