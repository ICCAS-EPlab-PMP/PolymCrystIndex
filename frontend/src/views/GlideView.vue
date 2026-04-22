<template>
  <div class="glide-view-page">
    <div class="main-container">
      <aside class="sidebar">
        <nav class="tab-nav">
          <button class="tab-item active" style="pointer-events: none;">
            <component :is="IconGlide" class="tab-icon" />
            <span class="tab-label">{{ t('glide.sidebarTitle') }}</span>
          </button>
        </nav>

        <div class="sidebar-footer">
          <div class="status-indicator">
            <span class="status-dot"></span>
            <span class="status-text">{{ t('glide.title') }}</span>
          </div>
        </div>
      </aside>

      <main class="content">
        <GlidePanel />
      </main>
    </div>
  </div>
</template>

<script setup>
import { defineAsyncComponent } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const GlidePanel = defineAsyncComponent(() => import('@/components/GlidePanel.vue'))

const IconGlide = {
  template: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
    <path d="M4 7h12l4 4H8z"/>
    <path d="M4 13h12l4 4H8z"/>
    <path d="M4 7v10"/>
  </svg>`
}
</script>

<style scoped>
.glide-view-page {
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
