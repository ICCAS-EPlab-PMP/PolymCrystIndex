<template>
  <div class="login-page">
    <div class="login-left">
      <div class="brand-section">
        <div class="logo-container">
          <img src="/icon.jpg" alt="PolymCrystIndex" />
        </div>
        <h1 class="brand-name">{{ t('app.name') }}</h1>
        <p class="brand-tagline">{{ t('brand.tagline') }}</p>
        
        <div class="features">
          <div class="feature">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
            <span>{{ t('brand.features.ga') }}</span>
          </div>
          <div class="feature">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 6v6l4 2"/>
            </svg>
            <span>{{ t('brand.features.realtime') }}</span>
          </div>
          <div class="feature">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
            </svg>
            <span>{{ t('brand.features.visualization') }}</span>
          </div>
        </div>

        <div class="citation">
          <p>{{ t('brand.citation') }}</p>
          <cite v-html="t('brand.citationText').replace(/\n/g, '<br>')"></cite>
        </div>
      </div>
    </div>

    <div class="login-right">
      <div class="lang-switch-login">
        <button
          :class="['lang-btn', { active: locale === 'en' }]"
          @click="setLocale('en')"
        >EN</button>
        <button
          :class="['lang-btn', { active: locale === 'zh' }]"
          @click="setLocale('zh')"
        >中文</button>
      </div>

      <div class="form-container">
        <div class="form-header">
          <h2>{{ isRegister ? t('login.createAccount') : t('login.welcomeBack') }}</h2>
          <p>{{ isRegister ? t('login.registerToStart') : t('login.signInToContinue') }}</p>
        </div>

        <form @submit.prevent="handleSubmit" class="login-form">
          <div class="form-group">
            <label for="username">{{ t('login.username') }}</label>
            <div class="input-wrapper">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              <input
                id="username"
                v-model="form.username"
                type="text"
                :placeholder="t('login.username')"
                required
              />
            </div>
          </div>

          <div class="form-group">
            <label for="password">{{ t('login.password') }}</label>
            <div class="input-wrapper">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0110 0v4"/>
              </svg>
              <input
                id="password"
                v-model="form.password"
                :type="showPassword ? 'text' : 'password'"
                :placeholder="t('login.password')"
                required
              />
              <button type="button" class="toggle-password" @click="showPassword = !showPassword">
                <svg v-if="!showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
              </button>
            </div>
          </div>

          <template v-if="isRegister">
            <div class="form-group">
              <label for="school">{{ t('login.school') }}</label>
              <div class="input-wrapper">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M22 10L12 5 2 10l10 5 10-5z"/>
                  <path d="M6 12v5c0 1.5 2.7 3 6 3s6-1.5 6-3v-5"/>
                </svg>
                <input
                  id="school"
                  v-model="form.school"
                  type="text"
                  :placeholder="t('login.schoolPlaceholder')"
                />
              </div>
            </div>

            <div class="form-group">
              <label for="organization">{{ t('login.organization') }}</label>
              <div class="input-wrapper">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="7" width="18" height="13" rx="2"/>
                  <path d="M16 20V4a1 1 0 00-1-1H9a1 1 0 00-1 1v16"/>
                  <path d="M8 11h8"/>
                </svg>
                <input
                  id="organization"
                  v-model="form.organization"
                  type="text"
                  :placeholder="t('login.organizationPlaceholder')"
                />
              </div>
            </div>
            <p class="register-hint">{{ t('login.sourceHint') }}</p>
          </template>

          <div v-if="errorMessage" class="error-message">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            {{ errorMessage }}
          </div>

          <button type="submit" class="btn-submit" :disabled="loading">
            <span v-if="loading" class="loading-spinner"></span>
            <span v-else>{{ isRegister ? t('login.createAccountBtn') : t('login.signIn') }}</span>
          </button>
        </form>

        <div class="form-footer">
          <p>
            {{ isRegister ? t('login.alreadyHaveAccount') : t('login.dontHaveAccount') }}
            <button type="button" @click="isRegister = !isRegister; errorMessage = ''">
              {{ isRegister ? t('login.signInInstead') : t('login.registerInstead') }}
            </button>
          </p>
        </div>


      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const { t, locale } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

const isRegister = ref(false)
const showPassword = ref(false)
const loading = ref(false)
const errorMessage = ref('')

const form = reactive({
  username: '',
  password: '',
  school: '',
  organization: ''
})

const setLocale = (loc) => {
  locale.value = loc
  localStorage.setItem('polymcrystindex-locale', loc)
}

const handleSubmit = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    if (isRegister.value) {
      if (!form.school.trim() && !form.organization.trim()) {
        errorMessage.value = t('login.sourceRequired')
        return
      }
      const result = await authStore.register({
        username: form.username,
        password: form.password,
        school: form.school.trim(),
        organization: form.organization.trim(),
      })
      if (result.success) {
        isRegister.value = false
        errorMessage.value = ''
        alert(t('login.registrationSuccess'))
      } else {
        errorMessage.value = result.message
      }
    } else {
      const result = await authStore.login(form.username, form.password)
      if (result.success) {
        router.push('/app/home')
      } else {
        errorMessage.value = result.message || t('login.invalidCredentials')
      }
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  min-height: 100vh;
  background: var(--bg-primary);
}

.login-left {
  flex: 1;
  background:
    radial-gradient(ellipse 120% 80% at 20% 10%, rgba(99, 179, 237, 0.38) 0%, transparent 50%),
    radial-gradient(ellipse 80% 100% at 85% 30%, rgba(16, 185, 129, 0.25) 0%, transparent 45%),
    radial-gradient(ellipse 60% 80% at 60% 85%, rgba(139, 92, 246, 0.18) 0%, transparent 50%),
    radial-gradient(ellipse 100% 60% at 10% 80%, rgba(59, 130, 246, 0.3) 0%, transparent 45%),
    radial-gradient(ellipse 70% 70% at 50% 50%, rgba(30, 64, 175, 0.5) 0%, transparent 70%),
    linear-gradient(165deg, #0f2a6e 0%, #1e3a8a 35%, #1e40af 65%, #0f2a6e 100%);
  color: var(--text-inverse);
  padding: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.login-left::before,
.login-left::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.login-left::before {
  background:
    linear-gradient(rgba(255, 255, 255, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.06) 1px, transparent 1px);
  background-size: 40px 40px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.5), transparent 90%);
}

.login-left::after {
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.12) 0%, transparent 40%, rgba(255, 255, 255, 0.02) 100%),
    radial-gradient(ellipse at 30% 20%, rgba(255, 255, 255, 0.08) 0%, transparent 50%);
}

.brand-section {
  max-width: 480px;
  text-align: center;
  position: relative;
  z-index: 1;
}

.logo-container {
  width: 180px;
  height: 180px;
  margin: 0 auto 24px;
  background: white;
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.logo-container img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 8px;
}

.brand-name {
  font-size: 2.5rem;
  font-weight: 700;
  margin-bottom: 12px;
  color: var(--text-inverse);
}

.brand-tagline {
  font-size: 1.125rem;
  opacity: 0.8;
  margin-bottom: 48px;
  line-height: 1.6;
}

.features {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 48px;
  text-align: left;
}

.feature {
  display: flex;
  align-items: center;
  gap: 16px;
  font-size: 1rem;
  opacity: 0.9;
}

.feature svg {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  opacity: 0.8;
}

.citation {
  padding-top: 32px;
  border-top: 1px solid rgba(255, 255, 255, 0.2);
  font-size: 0.875rem;
  opacity: 0.7;
  text-align: left;
}

.citation cite {
  font-style: normal;
  margin-top: 8px;
  display: block;
  line-height: 1.6;
}

.login-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  position: relative;
}

.lang-switch-login {
  position: absolute;
  top: 24px;
  right: 24px;
  display: flex;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-md);
  padding: 2px;
}

.lang-btn {
  padding: 6px 12px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.8125rem;
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

.form-container {
  width: 100%;
  max-width: 400px;
  animation: slideInUp 0.4s ease-out;
}

.form-header {
  text-align: center;
  margin-bottom: 32px;
}

.form-header h2 {
  font-size: 1.75rem;
  margin-bottom: 8px;
}

.form-header p {
  color: var(--text-secondary);
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.input-wrapper svg {
  position: absolute;
  left: 14px;
  width: 20px;
  height: 20px;
  color: var(--text-muted);
  pointer-events: none;
}

.input-wrapper input {
  width: 100%;
  padding: 14px 14px 14px 48px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 1rem;
  background: var(--bg-surface);
  transition: all var(--transition-fast);
}

.input-wrapper input:focus {
  outline: none;
  border-color: var(--border-focus);
  box-shadow: 0 0 0 3px var(--primary-bg);
}

.toggle-password {
  position: absolute;
  right: 14px;
  background: none;
  border: none;
  padding: 4px;
  color: var(--text-muted);
  transition: color var(--transition-fast);
}

.toggle-password:hover {
  color: var(--text-secondary);
}

.toggle-password svg {
  position: static;
  width: 20px;
  height: 20px;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--error-light);
  border-radius: var(--radius-md);
  color: var(--error);
  font-size: 0.875rem;
}

.register-hint {
  margin-top: -4px;
  margin-bottom: 8px;
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.error-message svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.btn-submit {
  width: 100%;
  padding: 14px 24px;
  background: var(--primary);
  color: var(--text-inverse);
  border: none;
  border-radius: var(--radius-md);
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-normal);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-submit:hover:not(:disabled) {
  background: var(--primary-dark);
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.btn-submit:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.form-footer {
  text-align: center;
  margin-top: 24px;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.form-footer button {
  background: none;
  border: none;
  color: var(--primary-light);
  font-weight: 500;
  cursor: pointer;
  transition: color var(--transition-fast);
}

.form-footer button:hover {
  color: var(--primary);
}

.demo-hint {
  margin-top: 32px;
  padding: 16px;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-md);
  text-align: center;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.demo-hint code {
  display: block;
  margin-top: 8px;
  font-size: 0.875rem;
  color: var(--primary);
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 1024px) {
  .login-left {
    display: none;
  }
}
</style>
