<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Chart from '../components/factory/Chart.vue';
import { useAuthStore } from '@/stores/auth'
import { useBacktestStore } from '@/stores/backtest'
import { useWebSocketStore } from '@/stores/websocket'
import { defineAsyncComponent } from 'vue'
import InlineTabs from '@/components/factory/InlineTabs.vue'

const authStore = useAuthStore()
const backtestStore = useBacktestStore()
const wsStore = useWebSocketStore()
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

// Function to automatically load the last backtest data
async function loadLastBacktestData() {
  if (!authStore.isAuthenticated) return;
  
  try {
    // Fetch all backtests for the user
    await backtestStore.fetchBacktests();
    
    // If there are backtests, get the most recent one
    if (backtestStore.backtests.length > 0) {
      // Sort by updated_at descending to get the most recent
      const sortedBacktests = [...backtestStore.backtests].sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );
      const lastBacktest = sortedBacktests[0];
      
      // Fetch the complete backtest data using the API
      await backtestStore.fetchBacktest(lastBacktest.id);
      
      // Get the backtest data from the store
      const backtestData = backtestStore.backtestById(lastBacktest.id);
      
      // If we have the data, set it in the WebSocket store for the chart
      if (backtestData) {
        wsStore.setChartDataFromBacktest(backtestData);
      }
    }
  } catch (error) {
    console.error('Error loading last backtest data:', error);
  }
}

onMounted(() => {
  // Load the last backtest data when the page loads
  loadLastBacktestData();
});
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
        <InlineTabs />
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
  background-color: var(--color-background-soft);
  border: 0px solid var(--color-border);
  position: relative; /* Necessary for positioning the overlay */
}

.chart-container.fullscreen {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background-color: var(--color-background);
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
