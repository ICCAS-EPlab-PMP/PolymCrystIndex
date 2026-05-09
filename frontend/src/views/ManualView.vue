<template>
  <div class="manual-view-page">
    <div class="main-container">
      <aside class="sidebar">
        <nav class="tab-nav">
          <button class="tab-item" :class="{ active: activeMode === 'cell' }" @click="activeMode = 'cell'">
            <component :is="IconManual" class="tab-icon" />
            <span class="tab-label">{{ t('manual.sidebarTitle') }}</span>
          </button>
          <button class="tab-item" :class="{ active: activeMode === 'supercell' }" @click="activeMode = 'supercell'">
            <component :is="IconSupercell" class="tab-icon" />
            <span class="tab-label">{{ t('manual.supercellTab') }}</span>
          </button>
        </nav>

        <div class="sidebar-footer">
          <div class="status-indicator">
            <span class="status-dot"></span>
            <span class="status-text">{{ activeTitle }}</span>
          </div>
        </div>
      </aside>

      <main class="content">
        <ManualCellPanel :mode="activeMode" />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const activeMode = ref('cell')
const activeTitle = computed(() => (activeMode.value === 'supercell' ? t('manual.supercellTab') : t('manual.sidebarTitle')))

const ManualCellPanel = defineAsyncComponent(() => import('@/components/ManualCellPanel.vue'))

const IconManual = {
  template: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
    <line x1="3" y1="9" x2="21" y2="9"/>
    <line x1="9" y1="3" x2="9" y2="21"/>
    <line x1="15" y1="3" x2="15" y2="21"/>
  </svg>`
}

const IconSupercell = {
  template: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <rect x="3" y="3" width="7" height="7" rx="1"/>
    <rect x="14" y="3" width="7" height="7" rx="1"/>
    <rect x="3" y="14" width="7" height="7" rx="1"/>
    <rect x="14" y="14" width="7" height="7" rx="1"/>
  </svg>`
}
</script>

<style scoped>
.manual-view-page {
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

@media (max-width: 1024px) {
  .sidebar {
    width: var(--sidebar-collapsed);
  }

  .tab-label,
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
