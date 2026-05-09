<template>
  <div class="results-page">
    <main class="main-content">
      <section class="results-section visualizer-section">
        <Visualizer :workDir="workDir" />
      </section>
      <section class="results-section export-section">
        <ResultExport mode="results-page" @navigate="handleNavigate" />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const Visualizer = defineAsyncComponent(() => import('@/components/Visualizer.vue'))
const ResultExport = defineAsyncComponent(() => import('@/components/ResultExport.vue'))
const route = useRoute()
const router = useRouter()

const workDir = computed(() => route.query.workDir || '')

const handleNavigate = (target) => {
  if (target === 'console') {
    router.push('/app/indexing')
  }
}
</script>

<style scoped>
.results-page {
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
  overflow: auto;
}

.results-section {
  min-width: 0;
}

.export-section {
  padding-bottom: 8px;
}
</style>
