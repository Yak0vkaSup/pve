

<script setup lang="ts">
import { ref, computed } from 'vue'
import Chart from '../components/factory/Chart.vue';
import Nodes from '../components/factory/Nodes.vue';
import { useAuthStore } from '@/stores/auth'
import Logs from '../components/factory/Logs.vue';
import { defineAsyncComponent } from 'vue'

const authStore = useAuthStore()
const isFullscreen = ref(false) // Track fullscreen state
function handleFullscreenToggle() {
  isFullscreen.value = !isFullscreen.value;
}

const ButtonsComponent = computed(() => {
  if (authStore.isAuthenticated) {
    return defineAsyncComponent(() => import('../components/factory/NodesSettings.vue'))
  } else {
    return {
      template: `<div></div>`
    }
  }
})
</script>

<template>
  <main class="main-content">
    <div class="factory-page">
      <div class="chart-container">
        <Chart :is-fullscreen="isFullscreen" @toggleFullscreen="handleFullscreenToggle" />
      </div>
      <div v-if="!isFullscreen" class="other-content">
        <div class="buttons-container">
          <component :is="ButtonsComponent" />
        </div>
        <div class="graph-container">
          <Nodes />
        </div>
        <div class="console-container">
          <Logs  />
        </div>
      </div>
    </div>
  </main>
</template>

<style scoped>

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  max-height: 200vh;
  max-width: 100vw;
}

.chart-container {
  width: 100%;
  height: 40vh;
  background-color: #2e2e2e;
  border: 0px solid #444;
  position: relative; /* Necessary for positioning the overlay */
}

.chart-container.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: #000;
  z-index: 1000;
}
.graph-container {
  min-height: 50vh;
}

canvas {
  width: 100%;
  height: 100%;
}


</style>
