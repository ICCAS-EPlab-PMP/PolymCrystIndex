<template>
  <div class="admin-layout">
    <header class="header">
      <div class="header-left">
        <div class="logo">
          <img src="@icon/index.jpg" alt="PolymCrystIndex" />
        </div>
        <div class="brand">
          <h1>{{ t('modules.admin.title') }}</h1>
          <span class="version">{{ t('app.version') }}</span>
        </div>
      </div>

      <div class="header-right">
        <div class="lang-switch">
          <button
            :class="['lang-btn', { active: locale === 'en' }]"
            @click="setLocale('en')"
          >EN</button>
          <button
            :class="['lang-btn', { active: locale === 'zh' }]"
            @click="setLocale('zh')"
          >中文</button>
        </div>

        <div class="user-info">
          <div class="user-avatar">
            {{ user?.displayName?.charAt(0)?.toUpperCase() || 'U' }}
          </div>
          <div class="user-details">
            <span class="user-name">{{ user?.displayName || 'User' }}</span>
            <span class="user-role">{{ t(`common.${user?.role || 'user'}`) }}</span>
          </div>
        </div>
        <button class="btn-logout" @click="handleLogout">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
            <polyline points="16,17 21,12 16,7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
          <span>{{ t('common.logout') }}</span>
        </button>
      </div>
    </header>

    <div class="admin-body">
      <aside class="admin-sidebar">
        <router-link to="/admin" class="sidebar-link">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="7" height="7"/>
            <rect x="14" y="3" width="7" height="7"/>
            <rect x="14" y="14" width="7" height="7"/>
            <rect x="3" y="14" width="7" height="7"/>
          </svg>
          <span>{{ t('admin.overview') || '概览' }}</span>
        </router-link>
        <router-link to="/admin/users" class="sidebar-link">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 00-3-3.87"/>
            <path d="M16 3.13a4 4 0 010 7.75"/>
          </svg>
          <span>{{ t('admin.users') || '用户管理' }}</span>
        </router-link>
        <router-link to="/admin/tasks" class="sidebar-link">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 11l3 3L22 4"/>
            <path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/>
          </svg>
          <span>{{ t('admin.tasks') || '任务审计' }}</span>
        </router-link>
        <router-link to="/admin/system" class="sidebar-link">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
          <span>{{ t('admin.system') || '系统状态' }}</span>
        </router-link>
        <div class="sidebar-divider"></div>
        <router-link to="/app/home" class="sidebar-link">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
            <polyline points="9,22 9,12 15,12 15,22"/>
          </svg>
          <span>{{ t('admin.backToUser') || '返回工作台' }}</span>
        </router-link>
      </aside>
      <main class="admin-main">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const { t, locale } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

const user = computed(() => authStore.state.user)

const setLocale = (loc) => {
  locale.value = loc
  localStorage.setItem('polymcrystindex-locale', loc)
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.admin-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--bg-primary);
}

.header {
  height: var(--header-height);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  position: sticky;
  top: 0;
  z-index: 50;
  box-shadow: var(--shadow-sm);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.logo {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  overflow: hidden;
  background: white;
  padding: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.logo img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.brand h1 {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text-primary);
}

.brand .version {
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: 'Fira Code', monospace;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 24px;
}

.lang-switch {
  display: flex;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-md);
  padding: 2px;
}

.lang-btn {
  padding: 8px 16px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.lang-btn:hover {
  color: var(--text-primary);
}

.lang-btn.active {
  background: var(--bg-surface);
  color: var(--primary);
  box-shadow: var(--shadow-sm);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--cta) 0%, var(--cta-light) 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 1rem;
}

.user-details {
  display: flex;
  flex-direction: column;
}

.user-name {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary);
}

.user-role {
  font-size: 0.75rem;
  color: var(--cta);
}

.btn-logout {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: 0.875rem;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.btn-logout:hover {
  background: var(--bg-surface-alt);
  border-color: var(--border-hover);
  color: var(--text-primary);
}

.btn-logout svg {
  width: 18px;
  height: 18px;
}

.admin-body {
  display: flex;
  flex: 1;
}

.admin-sidebar {
  width: 240px;
  background: var(--bg-surface);
  border-right: 1px solid var(--border);
  padding: 24px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  text-decoration: none;
  font-size: 0.9375rem;
  font-weight: 500;
  transition: all var(--transition-fast);
}

.sidebar-link:hover {
  background: var(--bg-surface-alt);
  color: var(--text-primary);
}

.sidebar-link.router-link-active {
  background: var(--primary-bg);
  color: var(--primary);
}

.sidebar-link svg {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.sidebar-divider {
  height: 1px;
  background: var(--border);
  margin: 16px 0;
}

.admin-main {
  flex: 1;
  padding: 32px;
  overflow-y: auto;
}

@media (max-width: 768px) {
  .admin-sidebar {
    width: 200px;
  }

  .admin-main {
    padding: 16px;
  }

  .header {
    padding: 0 16px;
  }

  .header-right {
    gap: 12px;
  }

  .user-details {
    display: none;
  }
}
</style>
