<template>
  <div class="user-layout">
    <header class="header">
      <div class="header-left">
        <div class="logo">
          <img src="@icon/index.jpg" alt="PolymCrystIndex" />
        </div>
        <div class="brand">
          <h1>{{ t('app.name') }}</h1>
          <span class="version">{{ t('app.version') }}</span>
        </div>
      </div>

      <div class="header-center">
        <span class="module-label">{{ currentModule.label }}</span>
        <div class="module-copy">
          <strong>{{ currentModule.title }}</strong>
          <span>{{ currentModule.desc }}</span>
        </div>
      </div>

      <div class="header-right">
        <button v-if="route.path !== '/app/home'" class="btn-home" @click="goHome">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
            <polyline points="9,22 9,12 15,12 15,22" />
          </svg>
          <span>{{ t('nav.return') }}</span>
        </button>

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

        <span v-if="isLocalProfile" class="local-badge">
          {{ t('common.localMode') }}
        </span>

        <button
          v-if="!isLocalProfile && isAdmin"
          class="user-info user-info-button"
          type="button"
          @click="goAdmin"
        >
          <div class="user-avatar">
            {{ user?.displayName?.charAt(0)?.toUpperCase() || 'U' }}
          </div>
          <div class="user-details">
            <span class="user-name">{{ user?.displayName || 'User' }}</span>
            <span class="user-role">{{ user?.role === 'admin' ? t('common.admin') : t('common.user') }}</span>
          </div>
        </button>
        <div v-else-if="!isLocalProfile" class="user-info">
          <div class="user-avatar">
            {{ user?.displayName?.charAt(0)?.toUpperCase() || 'U' }}
          </div>
          <div class="user-details">
            <span class="user-name">{{ user?.displayName || 'User' }}</span>
            <span class="user-role">{{ user?.role === 'admin' ? t('common.admin') : t('common.user') }}</span>
          </div>
        </div>
        <button v-if="!isLocalProfile" class="btn-logout" @click="handleLogout">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
            <polyline points="16,17 21,12 16,7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
          <span>{{ t('common.logout') }}</span>
        </button>
      </div>
    </header>

    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { isLocalProfile as getIsLocalProfile } from '@/services/runtime'

const { t, locale } = useI18n()
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const user = computed(() => authStore.state.user)
const isAdmin = computed(() => user.value?.role === 'admin')
const isLocalProfile = computed(() => getIsLocalProfile())

const currentModule = computed(() => {
  const key = route.meta?.moduleKey
  if (key === 'indexing') {
    return { label: 'Module', title: t('modules.indexing.title'), desc: t('modules.indexing.desc') }
  }
  if (key === 'glide') {
    return { label: 'Module', title: t('modules.glide.title'), desc: t('modules.glide.desc') }
  }
  if (key === 'manual') {
    return { label: 'Module', title: t('modules.manual.title'), desc: t('modules.manual.desc') }
  }
  if (key === 'results') {
    return { label: 'Module', title: t('modules.results.title'), desc: t('modules.results.desc') }
  }
  if (key === 'peakExtraction') {
    return { label: 'Module', title: t('modules.peakExtraction.title'), desc: t('modules.peakExtraction.desc') }
  }
  return { label: 'Workspace', title: t('home.selectModule'), desc: t('home.subtitle') }
})

const setLocale = (loc) => {
  locale.value = loc
  localStorage.setItem('polymcrystindex-locale', loc)
}

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

const goHome = () => {
  router.push('/app/home')
}

const goAdmin = () => {
  if (isAdmin.value) {
    router.push('/admin')
  }
}
</script>

<style scoped>
.user-layout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: linear-gradient(135deg, var(--bg-primary) 0%, #E8EDF5 100%);
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

.header-center {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 0 28px;
}

.module-label {
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--primary-bg);
  color: var(--primary);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  flex-shrink: 0;
}

.module-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.module-copy strong {
  font-size: 0.95rem;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.module-copy span {
  font-size: 0.75rem;
  color: var(--text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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
  font-size: 1.5rem;
  font-weight: 700;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
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

.btn-home,
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

.btn-home:hover,
.btn-logout:hover {
  background: var(--bg-surface-alt);
  border-color: var(--border-hover);
  color: var(--text-primary);
}

.btn-home svg,
.btn-logout svg {
  width: 18px;
  height: 18px;
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

.local-badge {
  padding: 6px 12px;
  background: var(--secondary);
  color: white;
  border-radius: var(--radius-md);
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-info-button {
  border: 1px solid transparent;
  background: transparent;
  border-radius: var(--radius-lg);
  padding: 6px 10px;
  transition: background var(--transition-fast), border-color var(--transition-fast);
}

.user-info-button:hover {
  background: var(--bg-surface-alt);
  border-color: var(--border);
}

.user-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%);
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
  color: var(--text-secondary);
}

.main-content {
  flex: 1;
  padding: 48px;
  display: flex;
  flex-direction: column;
  gap: 40px;
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  position: relative;
  isolation: isolate;
}

.main-content::before {
  content: '';
  position: fixed;
  inset: var(--header-height) 0 0 0;
  background:
    radial-gradient(circle at 12% 18%, rgba(59, 130, 246, 0.16), transparent 28%),
    radial-gradient(circle at 88% 8%, rgba(16, 185, 129, 0.12), transparent 22%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(248, 250, 252, 0.94));
  z-index: -2;
  pointer-events: none;
}

.main-content::after {
  content: '';
  position: fixed;
  inset: var(--header-height) 0 0 0;
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.45), transparent 92%);
  z-index: -1;
  pointer-events: none;
}

@media (max-width: 768px) {
  .main-content {
    padding: 24px;
  }

  .header {
    padding: 0 16px;
  }

  .header-right {
    gap: 12px;
  }

  .header-center {
    display: none;
  }

  .user-details {
    display: none;
  }

  .btn-home span,
  .btn-logout span {
    display: none;
  }
}
</style>
