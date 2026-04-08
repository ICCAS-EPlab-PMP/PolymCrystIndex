<template>
  <div class="results-page">
    <main class="main-content">
      <Visualizer />
    </main>
  </div>
</template>

<script setup>
import { defineAsyncComponent } from 'vue'

const Visualizer = defineAsyncComponent(() => import('@/components/Visualizer.vue'))
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
  overflow: hidden;
}
</style>
