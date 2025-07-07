<script setup lang="ts">
import { ref, computed } from 'vue';
import Chart           from '@/components/factory/Chart.vue';
import BotManagement   from '@/components/port/BotManagement.vue';

const isFullscreen = ref(false);
function handleFullscreenToggle() {
  isFullscreen.value = !isFullscreen.value;
}

/* helper to swap the class when fullscreen */
const chartClasses = computed(() =>
  ['chart-container', { fullscreen: isFullscreen.value }]
);
</script>

<template>
  <main class="main-content">
    <div class="port-page">
      <div :class="chartClasses">
        <Chart
          :is-fullscreen="isFullscreen"
          @toggleFullscreen="handleFullscreenToggle"
        />
      </div>

      <!-- show the rest of the UI only when chart is not in full-screen -->
      <div v-if="!isFullscreen" class="other-content">
        <BotManagement />
      </div>
    </div>
  </main>
</template>

<style scoped>
/* ---------- layout ---------- */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  max-height: 200vh;
  max-width: 100vw;
}

.chart-container {
  width: 100%;
  height: 60vh;
  background-color: var(--color-background-soft);
  border: 0px solid var(--color-border);
  position: relative;
}

.chart-container.fullscreen {
  position: fixed;
  top: 0; left: 0;
  width: 100vw; height: 100vh;
  background-color: var(--color-background);
  z-index: 1000;
}

.other-content {
  flex: 1;
  overflow: auto;
}

/* identical canvas sizing – keeps your existing chart styles */
canvas {
  width: 100%;
  height: 100%;
}
</style>
