<template>
  <div class="about">
    <div class="page-header glass-panel">
      <div class="page-header-content">
        <span class="eyebrow">PolymCrystIndex</span>
        <h2>{{ t('about.title') }}</h2>
        <p>{{ t('about.subtitle') }}</p>
      </div>
      <div class="header-highlight-card">
        <div class="highlight-label">{{ t('about.researchFocus') }}</div>
        <div class="highlight-value">{{ t('about.researchFocusTitle') }}</div>
        <p>{{ t('about.researchFocusDesc') }}</p>
      </div>
    </div>

    <div class="about-grid top-grid">
      <section class="about-section citation feature-panel">
        <div class="section-heading">
          <div class="section-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <div>
            <h3>{{ t('about.citation') }}</h3>
            <p class="section-subtitle">{{ t('about.citationSubtitle') }}</p>
          </div>
        </div>
        <div class="citation-box">
          <p class="citation-text">
            Ma, T., Hu, W., Wang, D. & Liu, G. (2025).<br>
            PolymCrystIndex: A genetic algorithm for automated polycrystalline fiber diffraction pattern indexing.<br>
            <em>J. Appl. Cryst.</em> 58, 759-767.
          </p>
          <a href="https://journals.iucr.org/paper?oc5041" target="_blank" class="btn-link">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/>
              <polyline points="15,3 21,3 21,9"/>
              <line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
            {{ t('about.viewPaper') }}
          </a>
        </div>
      </section>

      <section class="about-section acknowledgments feature-panel">
        <div class="section-heading">
          <div class="section-icon soft-green">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/>
            </svg>
          </div>
          <div>
            <h3>{{ t('about.acknowledgments') }}</h3>
            <p class="section-subtitle">{{ t('about.ackSubtitle') }}</p>
          </div>
        </div>
        <ul class="ack-list">
          <li>{{ t('about.ack1') }}</li>
          <li>{{ t('about.ack2') }}</li>
          <li>{{ t('about.ack3') }}</li>
          <li>{{ t('about.ack4') }}</li>
          <li>{{ t('about.ack5') }}</li>
          <li><a href="https://pyfai.readthedocs.io/en/stable/pyFAI.html" target="_blank">{{ t('about.ack6') }}</a></li>
        </ul>
      </section>

      <section class="about-section links feature-panel full-width">
        <div class="section-heading">
          <div class="section-icon soft-blue">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/>
              <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
            </svg>
          </div>
          <div>
            <h3>{{ t('about.friendlyLinks') }}</h3>
            <p class="section-subtitle">{{ t('about.linksSubtitle') }}</p>
          </div>
        </div>
        <div class="links-grid">
          <div class="link-card link-card-primary">
            <div class="link-logo polymcrystal">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/>
                <path d="M2 12l10 5 10-5"/>
              </svg>
            </div>
            <div class="link-info">
              <h4>{{ t('about.polymcrystal') }}</h4>
              <p>{{ t('about.polymcrystalDesc') }}</p>
            </div>
            <a href="http://www.polymcrystal.com/" target="_blank" class="btn-visit">
              {{ t('about.visit') }}
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="5" y1="12" x2="19" y2="12"/>
                <polyline points="12,5 19,12 12,19"/>
              </svg>
            </a>
          </div>

          <div class="link-card">
            <div class="link-logo iccas">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6l4 2"/>
              </svg>
            </div>
            <div class="link-info">
              <h4>{{ t('about.iccas') }}</h4>
              <p>{{ t('about.iccasDesc') }}</p>
            </div>
            <a href="https://www.iccas.ac.cn/" target="_blank" class="btn-visit">
              {{ t('about.visit') }}
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="5" y1="12" x2="19" y2="12"/>
                <polyline points="12,5 19,12 12,19"/>
              </svg>
            </a>
          </div>

          <div class="link-card">
            <div class="link-logo ep">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
                <line x1="3" y1="9" x2="21" y2="9"/>
                <line x1="9" y1="21" x2="9" y2="9"/>
              </svg>
            </div>
            <div class="link-info">
              <h4>{{ t('about.eplab') }}</h4>
              <p>{{ t('about.eplabDesc') }}</p>
            </div>
            <a href="http://eplab.iccas.ac.cn/" target="_blank" class="btn-visit">
              {{ t('about.visit') }}
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="5" y1="12" x2="19" y2="12"/>
                <polyline points="12,5 19,12 12,19"/>
              </svg>
            </a>
          </div>

          <div class="link-card">
            <div class="link-logo pyfai">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <polygon points="12,2 22,8.5 22,15.5 12,22 2,15.5 2,8.5"/>
                <line x1="12" y1="22" x2="12" y2="15.5"/>
                <polyline points="22,8.5 12,15.5 2,8.5"/>
              </svg>
            </div>
            <div class="link-info">
              <h4>{{ t('about.pmp') }}</h4>
              <p>{{ t('about.pmpDesc') }}</p>
            </div>
            <a href="http://pmp.iccas.ac.cn/" target="_blank" class="btn-visit">
              {{ t('about.visit') }}
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="5" y1="12" x2="19" y2="12"/>
                <polyline points="12,5 19,12 12,19"/>
              </svg>
            </a>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<style scoped>
.about {
  max-width: 1100px;
}

.page-header {
  margin-bottom: 32px;
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(260px, 0.9fr);
  gap: 24px;
  align-items: stretch;
}

.glass-panel {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(239, 246, 255, 0.92));
  border: 1px solid rgba(191, 219, 254, 0.7);
  border-radius: 24px;
  padding: 28px;
  box-shadow: 0 20px 50px rgba(30, 64, 175, 0.08);
}

.page-header-content {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.eyebrow {
  display: inline-flex;
  width: fit-content;
  margin-bottom: 12px;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(30, 64, 175, 0.08);
  color: var(--primary);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.page-header h2 {
  font-size: 2rem;
  margin-bottom: 12px;
}

.page-header p {
  color: var(--text-secondary);
  max-width: 60ch;
}

.header-highlight-card {
  padding: 24px;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(30, 64, 175, 0.98), rgba(30, 58, 138, 0.95));
  color: white;
  display: flex;
  flex-direction: column;
  justify-content: center;
  box-shadow: 0 16px 40px rgba(30, 64, 175, 0.18);
}

.highlight-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  opacity: 0.72;
  margin-bottom: 10px;
}

.highlight-value {
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: 10px;
}

.header-highlight-card p {
  color: rgba(255, 255, 255, 0.82);
}

.about-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr);
  gap: 24px;
}

.about-section {
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(226, 232, 240, 0.9);
  border-radius: 22px;
  padding: 24px;
}

.feature-panel {
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
}

.full-width {
  grid-column: 1 / -1;
}

.section-heading {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.section-icon {
  width: 48px;
  height: 48px;
  padding: 10px;
  background: var(--primary-bg);
  border-radius: var(--radius-md);
  color: var(--primary);
  margin-bottom: 16px;
}

.section-heading .section-icon {
  margin-bottom: 0;
}

.soft-green {
  background: rgba(16, 185, 129, 0.12);
  color: var(--secondary);
}

.soft-blue {
  background: rgba(59, 130, 246, 0.12);
  color: var(--primary-light);
}

.section-icon svg {
  width: 100%;
  height: 100%;
}

.about-section h3 {
  font-size: 1.25rem;
  margin-bottom: 6px;
  color: var(--text-primary);
}

.section-subtitle {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.citation-box {
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.9), rgba(239, 246, 255, 0.95));
  border-radius: 18px;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  border: 1px solid rgba(191, 219, 254, 0.6);
}

.citation-text {
  font-size: 0.9375rem;
  line-height: 1.8;
  color: var(--text-secondary);
}

.btn-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--primary);
  color: white;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 600;
  text-decoration: none;
  transition: all var(--transition-normal);
}

.btn-link:hover {
  background: var(--primary-dark);
  color: white;
  transform: translateY(-1px);
}

.btn-link svg {
  width: 16px;
  height: 16px;
}

.ack-list {
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ack-list li {
  padding: 12px 16px;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-md);
  font-size: 0.9375rem;
  color: var(--text-secondary);
  position: relative;
  padding-left: 32px;
}

.ack-list li::before {
  content: '✓';
  position: absolute;
  left: 12px;
  color: var(--secondary);
  font-weight: bold;
}

.links-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.link-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.95), rgba(241, 245, 249, 0.98));
  border-radius: 18px;
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.link-card-primary {
  background: linear-gradient(135deg, rgba(30, 64, 175, 0.08), rgba(59, 130, 246, 0.12));
  border-color: rgba(30, 64, 175, 0.25);
}

.link-card-primary .link-info h4 {
  color: var(--primary);
}

.link-card-primary .link-logo {
  background: var(--primary-bg);
  color: var(--primary);
}

.link-logo {
  width: 48px;
  height: 48px;
  padding: 10px;
  background: var(--bg-surface);
  border-radius: var(--radius-md);
  color: var(--primary);
  flex-shrink: 0;
}

.link-logo svg {
  width: 100%;
  height: 100%;
}

.link-info {
  flex: 1;
}

.link-info h4 {
  font-size: 0.9375rem;
  margin-bottom: 4px;
}

.link-info p {
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.btn-visit {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all var(--transition-fast);
}

.btn-visit:hover {
  border-color: var(--primary-light);
  color: var(--primary);
}

.btn-visit svg {
  width: 14px;
  height: 14px;
}

.top-grid {
  align-items: stretch;
}

.top-grid .about-section {
  height: 100%;
}

@media (max-width: 1024px) {
  .page-header,
  .about-grid {
    grid-template-columns: 1fr;
  }

  .links-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .glass-panel,
  .about-section {
    padding: 20px;
  }

  .section-heading {
    flex-direction: column;
  }
}
</style>
