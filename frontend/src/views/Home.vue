<template>
  <div class="home-page">
    <section v-if="isLocal" class="hero-panel">
      <div class="hero-copy">
        <span class="hero-eyebrow">{{ t('home.localBadge') }}</span>
        <div class="hero-kicker">{{ t('home.selectModule') }}</div>
        <h2>
          <span class="hero-title-brand">{{ t('home.title') }}</span>
          <span class="hero-title-sub">{{ t('home.subtitle') }}</span>
        </h2>
        <div class="hero-pill-row" aria-label="Workbench highlights">
          <span class="hero-pill">{{ t('home.labels.workbench') }}</span>
          <span class="hero-pill">{{ t('home.labels.workflow') }}</span>
          <span class="hero-pill">{{ t('home.labels.preprocess') }}</span>
          <span class="hero-pill">{{ t('home.labels.results') }}</span>
        </div>
      </div>
    </section>

    <div v-else class="welcome-section">
      <h2>{{ t('home.selectModule') }}</h2>
      <p>{{ t('home.subtitle') }}</p>
    </div>

    <div class="home-background-orb orb-one"></div>
    <div class="home-background-orb orb-two"></div>

    <div :class="isLocal ? 'workflow-grid' : 'cards-container'">
      <router-link to="/app/peak-extraction" class="feature-card">
        <div class="card-header">
          <div class="card-icon peak">
            <img :src="peakIcon" alt="Peak extraction module icon" class="module-icon-image" />
          </div>
          <div class="card-title">
            <h2>{{ t('modules.peakExtraction.title') }}</h2>
            <span v-if="!isLocal" class="badge active">{{ t('modules.active') }}</span>
          </div>
        </div>
        <div class="card-body">
          <p>{{ t('modules.peakExtraction.desc') }}</p>
        </div>
        <div class="card-footer">
          <div class="feature-tags">
            <span v-if="isLocal" class="feature-tag">{{ t('home.tags.rawImage') }}</span>
            <span v-if="isLocal" class="feature-tag">{{ t('home.tags.integration2d') }}</span>
            <span v-if="!isLocal" class="feature-tag">{{ t('nav.dataImport') }}</span>
            <span class="feature-tag">CSV Export</span>
          </div>
        </div>
      </router-link>

      <router-link to="/app/indexing" :class="['feature-card', isLocal ? 'featured-card' : '']">
        <div class="card-header">
          <div class="card-icon indexing">
            <img :src="indexIcon" alt="Indexing module icon" class="module-icon-image" />
          </div>
          <div class="card-title">
            <h2>{{ t('modules.indexing.title') }}</h2>
            <span v-if="!isLocal" class="badge active">{{ t('modules.active') }}</span>
          </div>
        </div>
        <div class="card-body">
          <p>{{ t('modules.indexing.desc') }}</p>
        </div>
        <div class="card-footer">
          <div class="feature-tags">
            <span class="feature-tag">{{ t('nav.dataImport') }}</span>
            <span class="feature-tag">{{ t('nav.parameters') }}</span>
            <span class="feature-tag">{{ t('nav.analysis') }}</span>
            <span class="feature-tag">{{ t('nav.results') }}</span>
          </div>
        </div>
      </router-link>

      <router-link to="/app/glide" class="feature-card">
        <div class="card-header">
          <div class="card-icon glide">
            <img :src="glideIcon" alt="Glide module icon" class="module-icon-image" />
          </div>
          <div class="card-title">
            <h2>{{ t('modules.glide.title') }}</h2>
            <span v-if="!isLocal" class="badge active">{{ t('modules.active') }}</span>
          </div>
        </div>
        <div class="card-body">
          <p>{{ t('modules.glide.desc') }}</p>
        </div>
        <div class="card-footer">
          <div class="feature-tags">
            <span class="feature-tag">{{ t('modules.glide.batchInput') }}</span>
            <span class="feature-tag">FullMiller</span>
          </div>
        </div>
      </router-link>

      <router-link to="/app/manual" class="feature-card">
        <div class="card-header">
          <div class="card-icon manual">
            <img :src="manualIcon" alt="Manual module icon" class="module-icon-image" />
          </div>
          <div class="card-title">
            <h2>{{ t('modules.manual.title') }}</h2>
            <span v-if="!isLocal" class="badge active">{{ t('modules.active') }}</span>
          </div>
        </div>
        <div class="card-body">
          <p>{{ t('modules.manual.desc') }}</p>
        </div>
        <div class="card-footer">
          <div class="feature-tags">
            <span class="feature-tag">{{ t('modules.manual.batchInput') }}</span>
            <span class="feature-tag">FullMiller</span>
          </div>
        </div>
      </router-link>

      <router-link to="/app/results" class="feature-card">
        <div class="card-header">
          <div class="card-icon results">
            <img :src="resultIcon" alt="Results module icon" class="module-icon-image" />
          </div>
          <div class="card-title">
            <h2>{{ t('modules.results.title') }}</h2>
            <span v-if="!isLocal" class="badge active">{{ t('modules.active') }}</span>
          </div>
        </div>
        <div class="card-body">
          <p>{{ t('modules.results.desc') }}</p>
        </div>
        <div class="card-footer">
          <div class="feature-tags">
            <span class="feature-tag">{{ t('modules.results.visualization') }}</span>
            <span class="feature-tag">{{ t('modules.results.export') }}</span>
            <span v-if="isLocal" class="feature-tag">HDF5</span>
          </div>
        </div>
      </router-link>
    </div>

    <section class="home-about">
      <About />
    </section>
  </div>
</template>

<script setup>
import { defineAsyncComponent, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { isLocalProfile } from '@/services/runtime'

const { t } = useI18n()

const About = defineAsyncComponent(() => import('@/views/About.vue'))

import peakIcon from '@icon/extract.svg'
import indexIcon from '@icon/index.svg'
import resultIcon from '@icon/result.svg'
import glideIcon from '@icon/glide.svg'
import manualIcon from '@icon/manual.svg'

const isLocal = computed(() => isLocalProfile())
</script>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  gap: 40px;
  position: relative;
  padding: 12px 0 4px;
  isolation: isolate;
}

.home-page::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(circle at 12% 18%, rgba(59, 130, 246, 0.16), transparent 28%),
    radial-gradient(circle at 88% 8%, rgba(16, 185, 129, 0.12), transparent 22%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.72), rgba(248, 250, 252, 0.94));
  z-index: -2;
}

.home-page::after {
  content: '';
  position: fixed;
  inset: 0;
  background-image:
    linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px);
  background-size: 28px 28px;
  mask-image: linear-gradient(180deg, rgba(0, 0, 0, 0.4), transparent 90%);
  z-index: -1;
  pointer-events: none;
}

.hero-panel {
  display: block;
  padding: 28px;
  border-radius: 28px;
  position: relative;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(226, 232, 240, 0.9);
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.08);
}

.hero-panel::before {
  content: '';
  position: absolute;
  inset: auto -120px -120px auto;
  width: 260px;
  height: 260px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.18), rgba(59, 130, 246, 0));
  pointer-events: none;
}

.hero-copy {
  position: relative;
  z-index: 1;
}

.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 6px 12px;
  color: var(--primary);
  background: var(--primary-bg);
  margin-bottom: 12px;
}

.hero-kicker {
  margin-bottom: 10px;
  font-size: 0.95rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(30, 64, 175, 0.76);
}

.hero-copy h2 {
  margin: 0 0 16px;
  display: flex;
  flex-direction: column;
  gap: 28px;
  line-height: 1.08;
  color: var(--text-primary);
}

.hero-title-brand {
  font-size: clamp(2.5rem, 5vw, 4.3rem);
  font-weight: 800;
  letter-spacing: -0.04em;
}

.hero-title-sub {
  font-size: clamp(1.05rem, 1.9vw, 1.4rem);
  font-weight: 600;
  margin-top: 8px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: rgba(15, 23, 42, 0.68);
}

.hero-pill-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
}

.hero-pill {
  display: inline-flex;
  align-items: center;
  padding: 7px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(191, 219, 254, 0.95);
  color: var(--text-primary);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  box-shadow: 0 12px 28px rgba(30, 64, 175, 0.08);
}

.welcome-section {
  text-align: center;
  animation: fadeInUp 0.6s ease-out;
  position: relative;
  z-index: 1;
}

.welcome-section h2 {
  font-size: 2rem;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.welcome-section p {
  font-size: 1.125rem;
  color: var(--text-secondary);
}

.cards-container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
  animation: fadeInUp 0.6s ease-out 0.1s both;
  position: relative;
  z-index: 1;
}

.workflow-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 22px;
  position: relative;
  z-index: 1;
}

.home-background-orb {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  filter: blur(10px);
  opacity: 0.55;
  z-index: -1;
}

.orb-one {
  width: 180px;
  height: 180px;
  top: 58px;
  left: -36px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.22) 0%, rgba(59, 130, 246, 0) 72%);
}

.orb-two {
  width: 220px;
  height: 220px;
  right: -30px;
  bottom: 24px;
  background: radial-gradient(circle, rgba(16, 185, 129, 0.16) 0%, rgba(16, 185, 129, 0) 72%);
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.feature-card {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  border-radius: var(--radius-xl);
  padding: 28px;
  cursor: pointer;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  border: 2px solid transparent;
  position: relative;
  overflow: hidden;
  min-height: 240px;
  display: flex;
  flex-direction: column;
  text-decoration: none;
}

.feature-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--primary), var(--primary-light));
  opacity: 0;
  transition: opacity 0.3s ease;
}

.featured-card {
  background: linear-gradient(180deg, rgba(239, 246, 255, 0.95), rgba(255, 255, 255, 0.92));
  border: 1px solid rgba(226, 232, 240, 0.9);
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.08);
}

.feature-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 20px 40px rgba(30, 64, 175, 0.15);
  text-decoration: none;
  border-color: rgba(59, 130, 246, 0.18);
}

.feature-card:hover::before {
  opacity: 1;
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}

.card-icon {
  width: 56px;
  height: 56px;
  border-radius: var(--radius-lg);
  background: #ffffff;
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.3s ease;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.08);
  overflow: hidden;
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.feature-card:hover .card-icon {
  transform: scale(1.1) rotate(5deg);
}

.module-icon-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  padding: 8px;
  transition: transform 0.3s ease;
}

.feature-card:hover .module-icon-image {
  transform: scale(1.04);
}

.card-icon.indexing {
  box-shadow: 0 12px 28px rgba(30, 64, 175, 0.16);
}

.card-icon.results {
  box-shadow: 0 12px 28px rgba(16, 185, 129, 0.14);
}

.card-icon.peak {
  box-shadow: 0 12px 28px rgba(139, 92, 246, 0.14);
}

.card-icon.glide {
  box-shadow: 0 12px 28px rgba(59, 130, 246, 0.16);
}

.card-icon.manual {
  box-shadow: 0 12px 28px rgba(139, 92, 246, 0.14);
}

.card-title {
  flex: 1;
}

.card-title h2 {
  font-size: 1.25rem;
  font-weight: 700;
  margin-bottom: 6px;
  color: var(--text-primary);
}

.badge {
  display: inline-block;
  font-size: 0.6875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 3px 10px;
  border-radius: 12px;
}

.badge.active {
  background: var(--secondary);
  color: white;
}

.card-body {
  flex: 1;
}

.card-body p {
  font-size: 0.9375rem;
  color: var(--text-secondary);
  line-height: 1.7;
}

.card-footer {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.feature-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.feature-tag {
  font-size: 0.75rem;
  padding: 4px 12px;
  background: var(--bg-surface-alt);
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  transition: all 0.2s ease;
}

.feature-card:hover .feature-tag {
  background: var(--primary-bg);
  color: var(--primary);
}

@media (max-width: 1024px) {
  .cards-container,
  .workflow-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .cards-container,
  .workflow-grid {
    grid-template-columns: 1fr;
  }

  .home-page {
    gap: 24px;
  }

  .hero-panel {
    padding: 20px;
  }

  .hero-title-brand {
    font-size: 2.2rem;
  }

  .hero-title-sub {
    letter-spacing: 0.12em;
  }
}

.home-about {
  margin-top: 40px;
  padding-top: 40px;
  position: relative;
  z-index: 1;
}

.home-about::before {
  content: '';
  position: absolute;
  inset: 0;
  background: transparent;
  z-index: -1;
}

.home-about :deep(.about) {
  max-width: none;
}

.home-about :deep(.glass-panel) {
  background: rgba(255, 255, 255, 0.82);
}

.home-about :deep(.about-section) {
  background: rgba(255, 255, 255, 0.82);
}

@media (prefers-reduced-motion: reduce) {
  .feature-card,
  .card-icon,
  .module-icon-image {
    transition: none;
  }
}
</style>
